import datetime as dt
from dataclasses import dataclass

import pytest
from rattler import PackageName, Version

from minimum_versions import release


@dataclass
class FakePackageRecord:
    name: PackageName
    version: Version
    build_number: int
    timestamp: dt.datetime


@pytest.fixture
def timestamps():
    yield [
        dt.datetime(2025, 12, 2, 20, 24, 40),
        dt.datetime(2025, 12, 2, 20, 25, 40),
        dt.datetime(2025, 12, 2, 20, 20, 40),
    ]


@pytest.fixture
def records(timestamps):
    yield [
        FakePackageRecord(
            name=PackageName("test1"),
            version=Version("1.0.0"),
            build_number=1,
            timestamp=timestamps[0],
        ),
        FakePackageRecord(
            name=PackageName("test1"),
            version=Version("1.0.1"),
            build_number=0,
            timestamp=None,
        ),
        FakePackageRecord(
            name=PackageName("test2"),
            version=Version("1.0.0"),
            build_number=0,
            timestamp=timestamps[2],
        ),
    ]


@pytest.fixture
def releases(timestamps):
    yield {
        "test1": [
            release.Release(
                version=Version("1.0.0"), build_number=1, timestamp=timestamps[0]
            ),
            release.Release(version=Version("1.0.1"), build_number=0, timestamp=None),
        ],
        "test2": [
            release.Release(
                version=Version("1.0.0"), build_number=0, timestamp=timestamps[2]
            )
        ],
    }


def test_release_from_repodata_record():
    repo_data = FakePackageRecord(
        name=PackageName("test"),
        version=Version("1.0.1"),
        build_number=0,
        timestamp=dt.datetime(2025, 12, 2, 20, 24, 40),
    )

    actual = release.Release.from_repodata_record(repo_data)

    assert actual.version == repo_data.version
    assert actual.build_number == repo_data.build_number
    assert actual.timestamp == repo_data.timestamp


def test_group_packages(records, releases):
    actual = release.group_packages(records)
    expected = releases

    assert actual == expected


@pytest.mark.parametrize(
    ["predicate", "expected"],
    (
        (
            lambda r: r.timestamp is None,
            {"test1": [release.Release(Version("1.0.1"), 0, None)], "test2": []},
        ),
        (
            lambda r: r.build_number == 1,
            {
                "test1": [
                    release.Release(
                        Version("1.0.0"), 1, dt.datetime(2025, 12, 2, 20, 24, 40)
                    )
                ],
                "test2": [],
            },
        ),
    ),
)
def test_filter_releases(releases, predicate, expected):
    actual = release.filter_releases(predicate, releases)
    assert actual == expected
