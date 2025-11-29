import pytest
from rattler import Version

from minimum_versions.environments import Spec, conda


@pytest.mark.parametrize(
    ["text", "expected_spec", "expected_name", "expected_warnings"],
    (
        ("numpy=1.23", Spec("numpy", Version("1.23")), "numpy", []),
        ("xarray=2024.10.0", Spec("xarray", Version("2024.10.0")), "xarray", []),
        (
            "xarray=2024.10.1",
            Spec("xarray", Version("2024.10.1")),
            "xarray",
            ["package should be pinned to a minor version (got 2024.10.1)"],
        ),
    ),
)
def test_parse_conda_spec(text, expected_spec, expected_name, expected_warnings):
    actual_spec, (actual_name, actual_warnings) = conda.parse_spec(text)

    assert actual_spec == expected_spec
    assert actual_name == expected_name
    assert actual_warnings == expected_warnings
