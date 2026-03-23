from pathlib import Path

from inspect_ai.log import (
    EvalConfig,
    EvalDataset,
    EvalLog,
    EvalResults,
    EvalSample,
    EvalSpec,
    read_eval_log,
    write_eval_log,
)
from inspect_flow._util.logs import num_valid_samples


def test_num_valid_samples_with_cleared_results(tmp_path: Path) -> None:
    log_path = str(tmp_path / "test.eval")
    samples = [
        EvalSample(id=i, epoch=1, input="hello", target="world") for i in range(1, 4)
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

    loaded = read_eval_log(log_path)
    assert num_valid_samples(loaded) == 3
    loaded.results = None
    write_eval_log(loaded, location=log_path)

    header = read_eval_log(log_path, header_only=True)
    assert num_valid_samples(header) == 3
