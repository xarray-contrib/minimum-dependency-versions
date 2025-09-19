import asyncio
import datetime
from dataclasses import dataclass, field

from rattler import Gateway, Version
from tlz.functoolz import curry, pipe
from tlz.itertoolz import concat, groupby


@dataclass(order=True)
class Release:
    version: Version
    build_number: int
    timestamp: datetime.datetime = field(compare=False)

    @classmethod
    def from_repodata_record(cls, repo_data):
        return cls(
            version=repo_data.version,
            build_number=repo_data.build_number,
            timestamp=repo_data.timestamp,
        )


def group_packages(records):
    groups = groupby(lambda r: r.name.normalized, records)
    return {
        name: sorted(map(Release.from_repodata_record, group))
        for name, group in groups.items()
    }


def filter_releases(predicate, releases):
    return {
        name: [r for r in records if predicate(r)] for name, records in releases.items()
    }


def deduplicate_releases(package_info):
    def deduplicate(releases):
        return min(releases, key=lambda p: p.timestamp)

    return {
        name: list(map(deduplicate, groupby(lambda p: p.version, group).values()))
        for name, group in package_info.items()
    }


def fetch_releases(channels, platforms, all_packages):
    gateway = Gateway()

    query = gateway.query(channels, platforms, all_packages, recursive=False)
    records = asyncio.run(query)

    return pipe(
        records,
        concat,
        group_packages,
        curry(filter_releases, lambda r: r.timestamp is not None),
        deduplicate_releases,
    )
