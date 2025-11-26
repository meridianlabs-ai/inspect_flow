MODEL_DUMP_ARGS = {
    "mode": "json",
    "exclude_unset": True,
    "exclude_defaults": True,  # Must exclude_defaults so that NotGiven fields are not serialized
    # do not exclude_none, as for NotGiven fields they are significant
}
