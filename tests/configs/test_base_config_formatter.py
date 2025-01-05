"""Testing for the config_formatter module."""

from unittest import mock

from pydantic import ValidationError

from djtools.configs.config_formatter import BaseConfigFormatter


def test_base_config_formatter_repr():
    """Define a sample subclass of BaseConfigFormatter for testing."""

    class SampleConfig(BaseConfigFormatter):
        """Dummy class."""

        field1: int
        field2: str

    config = SampleConfig(field1=42, field2="test")
    expected_repr = "SampleConfig(\n\tfield1=42\n\tfield2='test'\n)"
    assert repr(config) == expected_repr


def test_base_config_formatter_logging():
    """Define a class named "BaseConfig" to trigger the logging behavior."""
    with mock.patch("djtools.configs.config_formatter.logger") as mock_logger:

        class BaseConfig(BaseConfigFormatter):
            """Dummy class."""

            field: str

        _ = BaseConfig(field="test")
        mock_logger.info.assert_called_once_with(
            "BaseConfig(\n\tfield='test'\n)"
        )


def test_base_config_formatter_nested():
    """Define nested configurations."""

    class NestedConfig(BaseConfigFormatter):
        """Dummy class."""

        nested_field: int

    class ParentConfig(BaseConfigFormatter):
        """Dummy class."""

        parent_field: str
        nested: NestedConfig

    nested_config = NestedConfig(nested_field=99)
    parent_config = ParentConfig(parent_field="parent", nested=nested_config)

    expected_repr = (
        "ParentConfig(\n"
        "\tparent_field='parent'\n"
        "\tnested=NestedConfig(\n"
        "\t\tnested_field=99\n"
        "\t)\n"
        ")"
    )
    assert repr(parent_config) == expected_repr


def test_base_config_formatter_invalid():
    """Ensure invalid input raises a ValidationError."""

    class InvalidConfig(BaseConfigFormatter):
        """Dummy class."""

        field: int

    try:
        InvalidConfig(field="not an int")
        assert False, "Expected ValidationError was not raised"
    except ValidationError:
        pass


def test_base_config_formatter_list_of_dicts():
    """Test __repr__ for a field with a list of dictionaries."""

    class ConfigWithListOfDicts(BaseConfigFormatter):
        """Dummy class."""

        items: list[dict]

    config = ConfigWithListOfDicts(
        items=[{"key1": "value1"}, {"key2": "value2"}]
    )
    expected_repr = (
        "ConfigWithListOfDicts(\n"
        "\titems=[\n"
        "\t\t{'key1': 'value1'},\n"
        "\t\t{'key2': 'value2'}\n"
        "\t]\n"
        ")"
    )
    assert repr(config) == expected_repr
