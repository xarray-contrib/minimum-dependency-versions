import datetime as dt

import pytest
from rattler import Version

from minimum_versions.policy import Policy
from minimum_versions.release import Release


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
