import datetime
from dataclasses import dataclass, field

from rattler import Version


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
