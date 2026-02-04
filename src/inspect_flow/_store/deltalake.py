import json
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from logging import getLogger
from typing import Any, Counter, Sequence

import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from inspect_ai._eval.evalset import Log, task_identifier
from inspect_ai._util.file import dirname, exists, filesystem, to_uri
from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log
from inspect_ai.log._file import log_files_from_ls, read_eval_log_headers
from rich.progress import Progress, SpinnerColumn, TextColumn
from semver import Version
from typing_extensions import override

from inspect_flow._store.store import FlowStoreInternal, is_better_log
from inspect_flow._util.console import console, path, print
from inspect_flow._util.constants import PKG_NAME
from inspect_flow._util.error import NoLogsError
from inspect_flow._util.logging import PrefixLogger
from inspect_flow._util.path_util import path_str
from inspect_flow._util.util import now

logger = PrefixLogger(getLogger(__name__), prefix="flow-store")


def pa_field(pa_type: pa.DataType, **kwargs: Any) -> Any:
    """Create a dataclass field with PyArrow type metadata."""
    metadata = kwargs.pop("metadata", {})
    metadata["pa_type"] = pa_type
    return field(metadata=metadata, **kwargs)


TASK_IDENTIFIER_VERSION = 1  # TODO:ransom move to inspect_ai


def _task_id_col() -> str:
    return f"task_identifier_{TASK_IDENTIFIER_VERSION}"


def _escape_sql_string(s: str) -> str:
    return s.replace("'", "''")


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


LOGS = "_table_logs"


@dataclass
class LogRecord:
    log_path: str = pa_field(pa.string())
    task_identifier_1: str = pa_field(pa.string())
    ts: datetime = pa_field(pa.timestamp("ms"), default=None)

    def __post_init__(self) -> None:
        if self.ts is None:
            self.ts = now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def to_schema(cls) -> pa.Schema:
        return pa.schema([(f.name, f.metadata["pa_type"]) for f in fields(cls)])


TABLES: list[TableDef] = [
    TableDef(
        name=LOGS,
        version="0.2.0",
        schema=LogRecord.to_schema(),
    ),
]


def _create_table_description(table: TableDef) -> str:
    description = {"name": table.name, "version": table.version}
    return json.dumps(description)


def _check_table_description(table: TableDef, description: str) -> None:
    parsed = json.loads(description)
    if parsed.get("name") != table.name:
        raise ValueError(
            f"Table name mismatch: expected {table.name}, got {parsed.get('name')}"
        )
    if parsed.get("version") != table.version:
        stored = Version.parse(parsed.get("version"), optional_minor_and_patch=True)
        code = Version.parse(table.version, optional_minor_and_patch=True)
        if stored.major > code.major or stored.minor > code.minor:
            raise ValueError(
                f"Table {table.name} version mismatch: supported {table.version}, got {parsed.get('version')}. {PKG_NAME} upgrade required."
            )


# TODO:ransom move to inspect_ai
def list_all_eval_logs(log_dir: str, recursive: bool = True) -> list[Log]:
    log_files = list_eval_logs(log_dir, recursive=recursive)
    log_headers = read_eval_log_headers(log_files)
    task_identifiers = [task_identifier(log_header, None) for log_header in log_headers]
    return [
        Log(info=info, header=header, task_identifier=task_identifier)
        for info, header, task_identifier in zip(
            log_files, log_headers, task_identifiers, strict=True
        )
    ]


def _file_to_log(log_file: str) -> Log:
    info = filesystem(log_file).info(log_file)
    log_files = log_files_from_ls([info])
    if not log_files:
        raise NoLogsError(f"No log found: {log_file}")
    header = read_eval_log_headers([log_file])[0]
    task_id = task_identifier(header, None)
    assert task_id
    return Log(info=log_files[0], header=header, task_identifier=task_id)


def _eval_log_to_log(eval_log: EvalLog) -> Log:
    return _file_to_log(eval_log.location)


def _add_log_dir(
    log_dir: str, recursive: bool, dirs: set[str], logs: list[Log]
) -> None:
    if recursive:
        dirs.add(log_dir)
    dir_logs = list_all_eval_logs(log_dir=log_dir, recursive=recursive)
    if not dir_logs:
        raise NoLogsError(f"No logs found in directory: {log_dir}")
    logs.extend(dir_logs)
    dirs.add(to_uri(log_dir))
    if not recursive:
        logger.info(f"Found {path_str(log_dir)} with {len(dir_logs)} logs")
    else:
        subdirs = Counter[str]()
        for log in dir_logs:
            subdirs.update([to_uri(dirname(log.info.name))])
        for dir, count in subdirs.items():
            logger.info(f"Found {path_str(dir)} with {count} logs")


def _remove_path(
    path: str,
    recursive: bool,
    logs: set[str],
    logs_to_remove: set[str],
) -> None:
    path = to_uri(path)
    sep = filesystem(path).sep
    path_prefix = path if path.endswith(sep) else path + sep
    prefix_len = len(path_prefix)
    for log in list(logs):
        log = log.rstrip(sep)
        if log.startswith(path_prefix):
            if recursive:
                logs_to_remove.add(log)
            elif sep not in path[prefix_len:]:
                logs_to_remove.add(log)


class DeltaLakeStore(FlowStoreInternal):
    """Delta Lake implementation of FlowStore.

    Stores log directory paths in a Delta Lake table for scalable,
    concurrent-safe storage with S3 compatibility.
    """

    def __init__(self, store_path: str) -> None:
        self._store_path = store_path + filesystem(store_path).sep + "flow_store"

        self._fs = filesystem(self._store_path)
        self._storage_options = self._get_storage_options()
        found = [self._init_table(table) for table in TABLES]
        if any(found):
            print(f"\nUsing store: {path(store_path)}")
        else:
            print("\nStore not found")
            print(f"Creating store: {path(store_path)}", format="info")

    def _get_storage_options(self) -> dict[str, str] | None:
        if not self._fs.is_s3():
            return None
        bucket_name, _, _ = self._fs.fs.split_path(self._store_path)
        region = _get_bucket_region(bucket_name)

        options: dict[str, str] = {}
        if region:
            options["AWS_REGION"] = region

        # Support custom S3 endpoints (e.g., moto for testing, MinIO, LocalStack)
        if endpoint_url := os.environ.get("AWS_ENDPOINT_URL"):
            options["AWS_ENDPOINT_URL"] = endpoint_url
            # Allow HTTP for local testing endpoints
            if endpoint_url.startswith("http://127.0.0.1"):
                options["AWS_ALLOW_HTTP"] = "true"

        return options if options else None

    def _table_path(self, table_name: str) -> str:
        return f"{self._store_path}/{table_name}"

    def _open_table(self, table_name: str) -> DeltaTable:
        return DeltaTable(
            self._table_path(table_name),
            storage_options=self._storage_options,
        )

    def _get_table(self, table_path: str) -> DeltaTable | None:
        try:
            return DeltaTable(table_path, storage_options=self._storage_options)
        except (TableNotFoundError, OSError):
            return None

    def _init_table(self, table: TableDef) -> bool:
        table_path = self._table_path(table.name)
        if dt := self._get_table(table_path):
            logger.info(f"Existing table: {table_path}")
            _check_table_description(table, dt.metadata().description)
            return True
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
            return False

    @override
    def add_run_logs(self, eval_logs: list[EvalLog]) -> None:
        logs = [_eval_log_to_log(eval_log) for eval_log in eval_logs]
        self._add_logs(logs)

    @override
    def import_log_path(
        self,
        log_path: str | Sequence[str],
        recursive: bool = False,
    ) -> None:
        if isinstance(log_path, str):
            log_path = [log_path]
        # Collect dirs and logs to add
        dirs = set()
        logs: list[Log] = []
        for p in log_path:
            fs = filesystem(p)
            if not fs.exists(p):
                raise FileNotFoundError(f"Log path does not exist: {path_str(p)}")
            info = fs.info(p)
            if info.type == "file":
                logs.append(_file_to_log(p))
            else:
                dir = to_uri(p)
                _add_log_dir(log_dir=dir, recursive=recursive, dirs=dirs, logs=logs)
        self._add_logs(logs)

    @override
    def remove_log_path(
        self,
        log_path: str | Sequence[str],
        missing: bool = False,
        recursive: bool = False,
    ) -> None:
        if isinstance(log_path, str):
            log_path = [log_path]
        if not log_path:
            return

        logs = self.get_logs()
        logs_to_remove = set()
        for p in log_path:
            _remove_path(p, recursive, logs, logs_to_remove)
        if missing:
            logs_to_remove.update([log for log in logs if not exists(log)])

        if logs_to_remove:
            if num_deleted_rows := self._remove_logs(list(logs_to_remove)):
                logger.info(f"Removed {num_deleted_rows} logs from store")
            else:
                logger.info("No logs found to remove from store")

    def _remove_logs(self, logs_to_remove: Sequence[str]) -> int:
        if not logs_to_remove:
            return 0
        dt = self._open_table(LOGS)
        quoted_logs = ", ".join(
            f"'{_escape_sql_string(log)}'" for log in logs_to_remove
        )
        metrics = dt.delete(predicate=f"log_path IN ({quoted_logs})")
        return metrics.get("num_deleted_rows", 0)

    def _add_logs(self, logs: list[Log]) -> None:
        if not logs:
            return
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
                LogRecord(
                    log_path=to_uri(log.info.name),
                    task_identifier_1=log.task_identifier,
                ).to_dict()
                for log in new_logs
            ],
            schema=LogRecord.to_schema(),
        )

        write_deltalake(
            self._table_path(LOGS),
            new_data,
            mode="append",
            storage_options=self._storage_options,
        )

    @override
    def search_for_logs(self, task_ids: set[str]) -> dict[str, str]:
        results = dict()
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
                    logger.info(
                        f"Failed to read log {path_str(log)} referenced from the store. {e}"
                    )
                    continue
                if is_better_log(eval_log, best_eval_log):
                    best_log = log
                    best_eval_log = eval_log
            if best_log:
                results[task_id] = best_log
        return results

    @override
    def get_logs(self) -> set[str]:
        dt = self._open_table(LOGS)
        table = dt.to_pyarrow_table()
        return {path for path in table["log_path"].to_pylist() if path is not None}

    def _get_logs(self, task_ids: set[str]) -> dict[str, set[str]]:
        self._set_task_identifiers()

        dt = self._open_table(LOGS)
        dataset = dt.to_pyarrow_dataset()
        table = dataset.to_table(filter=pc.field(_task_id_col()).isin(task_ids))

        result: dict[str, set[str]] = {}
        for task_id, log_path in zip(
            table[_task_id_col()].to_pylist(),
            table["log_path"].to_pylist(),
            strict=True,
        ):
            if task_id not in result:
                result[task_id] = set()
            result[task_id].add(log_path)
        return result

    def _set_task_identifiers(self) -> None:
        """Find logs with missing task_identifier and compute it from the log header."""
        dt = self._open_table(LOGS)
        table = dt.to_pyarrow_table()

        # Find entries with empty or null task_identifier
        task_ids = table[_task_id_col()].to_pylist()
        log_paths = table["log_path"].to_pylist()

        log_paths_to_update: list[str] = [
            log_path
            for log_path, task_id in zip(log_paths, task_ids, strict=True)
            if not task_id and log_path is not None
        ]

        if not log_paths_to_update:
            return

        print("\nUpdating store task identifiers")
        logs_to_update: list[tuple[str, str]] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            console=console,
            transient=True,
        ) as progress:
            progress_task = progress.add_task(
                "Updating", total=len(log_paths_to_update)
            )
            for log_path in log_paths_to_update:
                try:
                    log = _file_to_log(log_path)
                    logs_to_update.append((log_path, log.task_identifier))
                except Exception as e:
                    logger.warning(f"Failed to read log {path_str(log_path)}: {e}")
                progress.advance(progress_task)

        if not logs_to_update:
            return

        # Update using merge
        update_table = pa.Table.from_pydict(
            {
                "log_path": [log_path for log_path, _ in logs_to_update],
                "task_identifier_1": [task_id for _, task_id in logs_to_update],
            }
        )

        dt.merge(
            source=update_table,
            predicate="target.log_path = source.log_path",
            source_alias="source",
            target_alias="target",
        ).when_matched_update({_task_id_col(): f"source.{_task_id_col()}"}).execute()
