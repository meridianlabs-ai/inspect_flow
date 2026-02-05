from inspect_flow._util.console import path


def test_path_highlights_task_name_in_log_path() -> None:
    log_path = "s3://bucket/2025-09-03T18-56-06+00-00_my-task_abc123.eval"
    result = path(log_path)

    # Verify the text content is preserved
    assert str(result) == log_path

    # Verify the task name is highlighted differently
    spans = result._spans
    assert len(spans) == 3

    # First span: prefix in magenta
    assert spans[0].style == "magenta"
    assert spans[0].end == log_path.find("my-task")

    # Second span: task name in highlight color
    assert spans[1].style == "#ffaaff"
    task_start = log_path.find("my-task")
    task_end = task_start + len("my-task")
    assert spans[1].start == task_start
    assert spans[1].end == task_end

    # Third span: suffix in magenta
    assert spans[2].style == "magenta"
    assert spans[2].start == task_end


def test_path_no_highlight_for_non_log_path() -> None:
    regular_path = "/some/regular/path/file.txt"
    result = path(regular_path)

    # Verify the text content is preserved
    assert str(result) == regular_path

    # Non-log paths should have no spans (base style applies to whole text)
    assert len(result._spans) == 0
