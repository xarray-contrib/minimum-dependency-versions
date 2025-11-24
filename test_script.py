import datetime as dt
import pathlib

import pytest
from rattler import Version

from minimum_versions import Policy, Release, Spec, _main


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
def test_spec_parse(text, expected_spec, expected_name, expected_warnings):
    actual_spec, (actual_name, actual_warnings) = Spec.parse(text)

    assert actual_spec == expected_spec
    assert actual_name == expected_name
    assert actual_warnings == expected_warnings


def test_error_missing_version_or_exclude():

    msg = (
        "No minimum version found for 'package_no_version_not_in_exclude' in"
        " 'failing-env2'. Either add a version or add to the list of excluded packages"
        " in the policy file."
    )

    with open("policy.yaml") as policy:

        environment_paths = [pathlib.Path("envs/failing-env2.yaml")]

        with pytest.raises(ValueError, match=msg):
            _main(dt.date(2023, 12, 12), policy, environment_paths=environment_paths)


@pytest.mark.parametrize(
    ["package_name", "policy", "today", "expected"],
    (
        (
            "numpy",
            Policy({"numpy": 6}, 12, {}),
            dt.date(2023, 12, 12),
            Release(Version("1.23.0"), 0, dt.datetime(2023, 6, 9)),
        ),
        (
            "scipy",
            Policy({"numpy": 6}, 8, {}),
            dt.date(2024, 9, 5),
            Release(Version("1.2.0"), 0, dt.datetime(2024, 1, 3)),
        ),
        (
            "scipy",
            Policy({"numpy": 6}, 8, overrides={"scipy": Version("1.1.1")}),
            dt.date(2024, 9, 5),
            Release(Version("1.1.1"), 0, dt.datetime(2023, 12, 1)),
        ),
    ),
)
def test_policy_minimum_version(package_name, policy, today, expected):
    releases = {
        "numpy": [
            Release(Version("1.22.0"), 0, dt.datetime(2022, 12, 1)),
            Release(Version("1.22.1"), 0, dt.datetime(2023, 2, 5)),
            Release(Version("1.23.0"), 0, dt.datetime(2023, 6, 9)),
            Release(Version("1.23.1"), 0, dt.datetime(2023, 8, 12)),
            Release(Version("1.23.2"), 0, dt.datetime(2023, 12, 5)),
        ],
        "scipy": [
            Release(Version("1.0.0"), 0, dt.datetime(2022, 11, 10)),
            Release(Version("1.0.1"), 0, dt.datetime(2023, 1, 13)),
            Release(Version("1.1.0"), 0, dt.datetime(2023, 9, 21)),
            Release(Version("1.1.1"), 0, dt.datetime(2023, 12, 1)),
            Release(Version("1.2.0"), 0, dt.datetime(2024, 1, 3)),
            Release(Version("1.2.1"), 0, dt.datetime(2024, 2, 5)),
        ],
    }

    actual = policy.minimum_version(today, package_name, releases[package_name])

    assert actual == expected
