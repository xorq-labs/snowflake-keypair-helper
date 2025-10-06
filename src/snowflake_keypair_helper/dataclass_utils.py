from typing import Any


def validate_dataclass_types(instance):
    gen = (
        (name, field.type, getattr(instance, name))
        for (name, field) in instance.__dataclass_fields__.items()
    )
    if bad_values := tuple(
        (name, expected, type(value))
        for name, expected, value in gen
        if expected is not Any and not isinstance(value, expected)
    ):
        raise ValueError(bad_values)
