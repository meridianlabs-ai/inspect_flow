from pathlib import Path

import pytest
from inspect_ai.log import (
    EvalConfig,
    EvalDataset,
    EvalLog,
    EvalResults,
    EvalSample,
    EvalSpec,
    ProvenanceData,
    invalidate_samples,
    read_eval_log,
    write_eval_log,
)
from inspect_flow._util.logs import num_valid_samples


@pytest.fixture
def eval_log(tmp_path: Path) -> str:
    log_path = str(tmp_path / "test.eval")
    samples = [
        EvalSample(id=i, epoch=1, input="hello", target="world", uuid=f"uuid-{i}")
        for i in range(1, 4)
    ]
    log = EvalLog(
        status="success",
        eval=EvalSpec(
            created="2024-01-01T00:00:00+00:00",
            task="test_task",
            dataset=EvalDataset(),
            model="mockllm/model",
            config=EvalConfig(),
        ),
        results=EvalResults(total_samples=3, completed_samples=3),
        samples=samples,
    )
    write_eval_log(log, location=log_path)
    return log_path


def test_num_valid_samples_with_cleared_results(eval_log: str) -> None:
    loaded = read_eval_log(eval_log)
    assert num_valid_samples(loaded) == 3
    loaded.results = None
    write_eval_log(loaded, location=eval_log)

    header = read_eval_log(eval_log, header_only=True)
    assert num_valid_samples(header) == 3


def test_num_valid_samples_with_invalidated_samples(eval_log: str) -> None:
    loaded = read_eval_log(eval_log)
    loaded = invalidate_samples(
        loaded, sample_uuids=["uuid-1"], provenance=ProvenanceData(author="test")
    )
    write_eval_log(loaded, location=eval_log)

    header = read_eval_log(eval_log, header_only=True)
    assert num_valid_samples(header) == 2
