import json
from dataclasses import dataclass
from logging import Logger, LoggerAdapter, getLogger
from typing import Any, Counter, MutableMapping, Sequence

import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import Log, task_identifier
from inspect_ai._util.file import dirname, filesystem, to_uri
from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_ai.log._file import read_eval_log_headers
from semver import Version

from inspect_flow._store.store import FlowStoreInternal, is_better_log
from inspect_flow._util.constants import PKG_NAME
from inspect_flow._util.error import NoLogsError
from inspect_flow._util.path_util import path_str


class PrefixLogger(LoggerAdapter):
    def __init__(self, logger: Logger, prefix: str) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        return f"[{self.prefix}] {msg}", kwargs


logger = PrefixLogger(getLogger(__name__), prefix="flow-store")

TASK_IDENTIFIER_VERSION = 1  # TODO:ransom move to inspect_ai


def _get_bucket_region(bucket_name: str) -> str | None:
    """Get the region for an S3 bucket using the AWS API."""
    try:
        import boto3

        s3_client = boto3.client("s3")
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        # LocationConstraint is None for us-east-1
        return response.get("LocationConstraint") or "us-east-1"
    except Exception as e:
        logger.warning(f"Failed to get bucket region for {bucket_name}: {e}")
        return None


@dataclass
class TableDef:
    name: str
    version: str
    schema: pa.Schema


LOG_DIRS = "log_dirs"
LOG_DIRS_SCHEMA = pa.schema([("log_dir", pa.string())])

LOGS = "logs"
LOGS_SCHEMA = pa.schema(
    [
        ("task_identifier", pa.string()),
        ("log_path", pa.string()),
    ]
)

TABLES: list[TableDef] = [
    TableDef(
        name=LOG_DIRS,
        version="0.1",
        schema=LOG_DIRS_SCHEMA,
    ),
    TableDef(
        name=LOGS,
        version="0.1",
        schema=LOGS_SCHEMA,
    ),
]


def _create_table_description(table: TableDef) -> str:
    description = {"name": table.name, "version": table.version}
    if table.name == LOGS:
        description["task_identifier_version"] = str(TASK_IDENTIFIER_VERSION)
    return json.dumps(description)


def _check_table_description(table: TableDef, description: str) -> None:
    parsed = json.loads(description)
    if parsed.get("name") != table.name:
        raise ValueError(
            f"Table name mismatch: expected {table.name}, got {parsed.get('name')}"
        )
    if parsed.get("version") != table.version:
        stored = Version.parse(parsed.get("version"))
        code = Version.parse(table.version)
        if stored > code:
            raise ValueError(
                f"Table {table.name} version mismatch: supported {table.version}, got {parsed.get('version')}. {PKG_NAME} upgrade required."
            )
        else:
            raise ValueError(
                f"Table {table.name} version mismatch: supported {table.version}, got {parsed.get('version')}. Store upgrade required."
            )
    if table.name == LOGS:
        if parsed.get("task_identifier_version") != str(TASK_IDENTIFIER_VERSION):
            raise ValueError(
                f"Table {table.name} task identifier version mismatch: expected {TASK_IDENTIFIER_VERSION}, got {parsed.get('task_identifier_version')}. Store update required."
            )


# TODO:ransom move to inspect_ai
def list_all_eval_logs(log_dir: str, recursive: bool = True) -> list[Log]:
    log_files = list_eval_logs(log_dir, recursive=recursive)
    log_headers = read_eval_log_headers(log_files)
    task_identifiers = [
        task_identifier(log_header, None, None) for log_header in log_headers
    ]
    return [
        Log(info=info, header=header, task_identifier=task_identifier)
        for info, header, task_identifier in zip(
            log_files, log_headers, task_identifiers, strict=True
        )
    ]


def _add_log_dir(
    log_dir: str, recursive: bool, dirs: set[str], logs: list[Log]
) -> None:
    dir_logs = list_all_eval_logs(log_dir=log_dir, recursive=recursive)
    if not dir_logs:
        raise NoLogsError(f"No logs found in directory: {log_dir}")
    logs.extend(dir_logs)
    if not recursive:
        logger.info(f"Adding {path_str(log_dir)} with {len(dir_logs)} logs")
        dirs.add(to_uri(dirname(dir_logs[0].info.name)))
    else:
        subdirs = Counter[str]()
        for log in dir_logs:
            subdirs.update([to_uri(dirname(log.info.name))])
        for dir, count in subdirs.items():
            logger.info(f"Adding {path_str(dir)} with {count} logs")
        dirs.update(subdirs.keys())


class DeltaLakeStore(FlowStoreInternal):
    """Delta Lake implementation of FlowStore.

    Stores log directory paths in a Delta Lake table for scalable,
    concurrent-safe storage with S3 compatibility.
    """

    def __init__(self, store_path: str) -> None:
        self._store_path = store_path
        self._fs = filesystem(store_path)
        self._storage_options = self._get_storage_options()
        for table in TABLES:
            self._init_table(table)

    def _get_storage_options(self) -> dict[str, str] | None:
        if not self._fs.is_s3():
            return None
        bucket_name, _, _ = self._fs.fs.split_path(self._store_path)
        region = _get_bucket_region(bucket_name)

        if region:
            return {"AWS_REGION": region}
        return None

    def _table_path(self, table_name: str) -> str:
        return f"{self._store_path}/{table_name}"

    def _get_table(self, table_path: str) -> DeltaTable | None:
        try:
            return DeltaTable(table_path, storage_options=self._get_storage_options())
        except (TableNotFoundError, OSError):
            return None

    def _init_table(self, table: TableDef) -> None:
        table_path = self._table_path(table.name)
        if dt := self._get_table(table_path):
            logger.info(f"Existing table: {table_path}")
            _check_table_description(table, dt.metadata().description)
        else:
            logger.info(f"Creating table: {table_path}")
            fs = filesystem(table_path)
            # Create _store_path first to make it less likely to need to create an s3 bucket, which can cause errors
            fs.mkdir(self._store_path, exist_ok=True)
            fs.mkdir(table_path, exist_ok=True)
            metadata = _create_table_description(table)
            empty_table = pa.Table.from_pylist([], schema=table.schema)
            write_deltalake(
                table_path,
                empty_table,
                description=metadata,
                storage_options=self._storage_options,
            )

    def add_log_dir(
        self, log_dir: str | Sequence[str], recursive: bool = False
    ) -> None:
        if isinstance(log_dir, str):
            log_dir = [log_dir]
        dirs = set()
        logs = []
        for dir in log_dir:
            dir = to_uri(dir)
            _add_log_dir(log_dir=dir, recursive=recursive, dirs=dirs, logs=logs)
        existing_dirs = self.get_log_dirs()
        new_dirs = dirs - existing_dirs
        if new_dirs:
            if not self._fs.is_local():
                for dir in new_dirs:
                    if filesystem(dir).is_local():
                        raise ValueError(
                            f"""Local log directories cannot be added to remote stores.

Local log directory:
  {path_str(dir)}

Remote store:
  {path_str(self._store_path)}

Use a log directory on remote storage (e.g., s3://<bucket>/<path>)."""
                        )

            new_data = pa.Table.from_pylist(
                [{"log_dir": log_dir} for log_dir in new_dirs],
                schema=LOG_DIRS_SCHEMA,
            )

            write_deltalake(
                self._table_path(LOG_DIRS),
                new_data,
                mode="append",
                storage_options=self._storage_options,
            )

        if logs:
            self._add_logs(logs)

    def remove_log_dir(self, log_dir: str | Sequence[str]) -> None:
        if isinstance(log_dir, str):
            log_dir = [log_dir]

        if not log_dir:
            return

        log_dir = [to_uri(d) for d in log_dir]
        dt = DeltaTable(
            self._table_path(LOG_DIRS),
            storage_options=self._storage_options,
        )
        quoted_dirs = ", ".join(f"'{d}'" for d in log_dir)
        metrics = dt.delete(predicate=f"log_dir IN ({quoted_dirs})")
        if num_deleted_rows := metrics.get("num_deleted_rows", 0):
            logger.info(f"Removed {num_deleted_rows} log directories")
            self.refresh()
        else:
            logger.info("No log directories found to remove")

    def refresh(self) -> None:
        log_dirs = self.get_log_dirs()

        all_logs = []
        for log_dir in log_dirs:
            logs = list_all_eval_logs(log_dir=log_dir)
            all_logs.extend(logs)

        new_data = pa.Table.from_pylist(
            [
                {
                    "task_identifier": log.task_identifier,
                    "log_path": to_uri(log.info.name),
                }
                for log in all_logs
            ],
            schema=LOGS_SCHEMA,
        )

        write_deltalake(
            self._table_path(LOGS),
            new_data,
            mode="overwrite",
            storage_options=self._storage_options,
        )

    def _add_logs(self, logs: list[Log], overwrite: bool = False) -> None:
        task_ids = {log.task_identifier for log in logs}
        existing_logs = self._get_logs(task_ids)
        new_logs = [
            log
            for log in logs
            if to_uri(log.info.name)
            not in existing_logs.get(log.task_identifier, set())
        ]
        if not new_logs:
            return

        new_data = pa.Table.from_pylist(
            [
                {
                    "task_identifier": log.task_identifier,
                    "log_path": to_uri(log.info.name),
                }
                for log in new_logs
            ],
            schema=LOGS_SCHEMA,
        )

        write_deltalake(
            self._table_path(LOGS),
            new_data,
            mode="append",
            storage_options=self._storage_options,
        )

    def search_for_logs(self, task_ids: set[str]) -> list[str]:
        results = []
        remaining_task_ids = set(task_ids)

        indexed_logs = self._get_logs(remaining_task_ids)
        for task_id in list(remaining_task_ids):
            if task_id not in indexed_logs:
                continue
            logs = indexed_logs[task_id]
            best_log = None
            best_eval_log = None
            for log in logs:
                try:
                    eval_log = read_eval_log(log, header_only=True)
                except Exception as e:
                    logger.error(
                        f"Failed to read log {path_str(log)} referenced from the store. This could be a permissions issue. Use 'flow store remove' to update the store. {e}"
                    )
                    raise
                if is_better_log(eval_log, best_eval_log):
                    best_log = log
                    best_eval_log = eval_log
            if best_log:
                results.append(best_log)
        return results

    def get_log_dirs(self) -> set[str]:
        dt = DeltaTable(
            self._table_path(LOG_DIRS),
            storage_options=self._storage_options,
        )
        table = dt.to_pyarrow_table()
        return set(table["log_dir"].to_pylist())

    def get_logs(self) -> set[str]:
        dt = DeltaTable(
            self._table_path(LOGS),
            storage_options=self._storage_options,
        )
        table = dt.to_pyarrow_table()
        return set(table["log_path"].to_pylist())

    def _get_logs(self, task_ids: set[str]) -> dict[str, set[str]]:
        dt = DeltaTable(
            self._table_path(LOGS),
            storage_options=self._storage_options,
        )
        dataset = dt.to_pyarrow_dataset()
        table = dataset.to_table(filter=pc.field("task_identifier").isin(task_ids))

        result: dict[str, set[str]] = {}
        for task_id, log_path in zip(
            table["task_identifier"].to_pylist(),
            table["log_path"].to_pylist(),
            strict=True,
        ):
            if task_id not in result:
                result[task_id] = set()
            result[task_id].add(log_path)
        return result
