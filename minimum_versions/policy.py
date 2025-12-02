import bisect
from dataclasses import dataclass, field

import jsonschema
import yaml
from dateutil.relativedelta import relativedelta
from rattler import Version

schema = {
    "type": "object",
    "properties": {
        "channels": {"type": "array", "items": {"type": "string"}},
        "platforms": {"type": "array", "items": {"type": "string"}},
        "policy": {
            "type": "object",
            "properties": {
                "packages": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-z][a-z0-9_-]*$": {"type": "integer", "minimum": 1}
                    },
                    "additionalProperties": False,
                },
                "default": {"type": "integer", "minimum": 1},
                "overrides": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-z][a-z0-9_-]*": {"type": "string", "format": "date"}
                    },
                    "additionalProperties": False,
                },
                "exclude": {"type": "array", "items": {"type": "string"}},
                "ignored_violations": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[a-z][a-z0-9_-]*$"},
                },
            },
            "required": [
                "packages",
                "default",
                "overrides",
                "exclude",
                "ignored_violations",
            ],
        },
    },
    "required": ["channels", "platforms", "policy"],
}


def find_release(releases, version):
    index = bisect.bisect_left(releases, version, key=lambda x: x.version)
    return releases[index]


def is_suitable_release(release):
    if release.timestamp is None:
        return False

    segments = release.version.extend_to_length(3).segments()

    return segments[2] == [0]


@dataclass
class Policy:
    package_months: dict
    default_months: int

    channels: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)

    overrides: dict[str, Version] = field(default_factory=dict)

    ignored_violations: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    def minimum_version(self, today, package_name, releases):
        if (override := self.overrides.get(package_name)) is not None:
            return find_release(releases, version=override)

        suitable_releases = [
            release for release in releases if is_suitable_release(release)
        ]
        if not suitable_releases:
            raise ValueError(f"Cannot find valid releases for {package_name}")

        policy_months = self.package_months.get(package_name, self.default_months)

        cutoff_date = today - relativedelta(months=policy_months)

        index = bisect.bisect_left(
            suitable_releases, cutoff_date, key=lambda x: x.timestamp.date()
        )

        return suitable_releases[index - 1 if index > 0 else 0]


def parse_policy(f):
    policy = yaml.safe_load(f)

    try:
        jsonschema.validate(instance=policy, schema=schema)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            f"Invalid policy definition: {str(e)}"
        ) from None

    package_policy = policy["policy"]

    return Policy(
        channels=policy["channels"],
        platforms=policy["platforms"],
        exclude=package_policy["exclude"],
        package_months=package_policy["packages"],
        default_months=package_policy["default"],
        ignored_violations=package_policy["ignored_violations"],
        overrides=package_policy["overrides"],
    )


def find_policy_versions(policy, today, releases):
    return {
        name: policy.minimum_version(today, name, package_releases)
        for name, package_releases in releases.items()
    }
