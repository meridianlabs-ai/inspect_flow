from inspect_flow._util.path_util import apply_bundle_url_mappings


def test_apply_bundle_url_mappings_trailing_slash_on_value() -> None:
    # Reproduces a double-slash bug: the launcher strips trailing slashes from
    # mapping keys via absolute_path_relative_to, but values retain their trailing
    # slash. The result should not contain a double slash.
    result = apply_bundle_url_mappings(
        "s3://flow-view/bundle",
        {"s3://flow-view": "http://flow-view.s3-website.us-east-2.amazonaws.com/"},
    )
    assert result == "http://flow-view.s3-website.us-east-2.amazonaws.com/bundle"
    assert "//" not in result.removeprefix("http://")
