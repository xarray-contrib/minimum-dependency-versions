import asyncio
import bisect
import datetime
import pathlib
import sys
from dataclasses import dataclass, field

import jsonschema
import rich_click as click
import yaml
from dateutil.relativedelta import relativedelta
from rattler import Gateway, Version
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Column, Table
from tlz.functoolz import curry, pipe
from tlz.itertoolz import concat, groupby

click.rich_click.SHOW_ARGUMENTS = True


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
                        "^[a-z][-a-z_]*$": {"type": "integer", "minimum": 1}
                    },
                    "additionalProperties": False,
                },
                "default": {"type": "integer", "minimum": 1},
                "overrides": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-z][-a-z_]*": {"type": "string", "format": "date"}
                    },
                    "additionalProperties": False,
                },
                "exclude": {"type": "array", "items": {"type": "string"}},
                "ignored_violations": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[a-z][-a-z_]*$"},
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

        policy_months = self.package_months.get(package_name, self.default_months)

        cutoff_date = today - relativedelta(months=policy_months)

        index = bisect.bisect_left(
            suitable_releases, cutoff_date, key=lambda x: x.timestamp.date()
        )
        return suitable_releases[index - 1 if index > 0 else 0]


@dataclass
class Spec:
    name: str
    version: Version | None

    @classmethod
    def parse(cls, spec_text):
        warnings = []
        if ">" in spec_text or "<" in spec_text:
            warnings.append(
                f"package must be pinned with an exact version: {spec_text!r}. Using the version as an exact pin instead."
            )

            spec_text = spec_text.replace(">", "").replace("<", "")

        if "=" in spec_text:
            name, version_text = spec_text.split("=", maxsplit=1)
            version = Version(version_text)
            segments = version.segments()

            if (len(segments) == 3 and segments[2] != [0]) or len(segments) > 3:
                warnings.append(
                    f"package should be pinned to a minor version (got {version})"
                )
        else:
            name = spec_text
            version = None

        return cls(name, version), (name, warnings)


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


def parse_environment(text):
    env = yaml.safe_load(text)

    specs = []
    warnings = []
    for dep in env["dependencies"]:
        spec, warnings_ = Spec.parse(dep)

        specs.append(spec)
        warnings.append(warnings_)

    return specs, warnings


def parse_policy(file):
    policy = yaml.safe_load(file)
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


def is_preview(version):
    candidates = {"rc", "b", "a"}

    *_, last_segment = version.segments()
    return any(candidate in last_segment for candidate in candidates)


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


def find_release(releases, version):
    index = bisect.bisect_left(releases, version, key=lambda x: x.version)
    return releases[index]


def deduplicate_releases(package_info):
    def deduplicate(releases):
        return min(releases, key=lambda p: p.timestamp)

    return {
        name: list(map(deduplicate, groupby(lambda p: p.version, group).values()))
        for name, group in package_info.items()
    }


def find_policy_versions(policy, today, releases):
    return {
        name: policy.minimum_version(today, name, package_releases)
        for name, package_releases in releases.items()
    }


def is_suitable_release(release):
    if release.timestamp is None:
        return False

    segments = release.version.extend_to_length(3).segments()

    return segments[2] == [0]


def lookup_spec_release(spec, releases):
    version = spec.version.extend_to_length(3)

    return releases[spec.name][version]


def compare_versions(environments, policy_versions, ignored_violations):
    status = {}
    for env, specs in environments.items():
        env_status = any(
            (
                spec.name not in ignored_violations
                and spec.version > policy_versions[spec.name].version
            )
            for spec in specs
        )
        status[env] = env_status
    return status


def version_comparison_symbol(required, policy):
    if required < policy:
        return "<"
    elif required > policy:
        return ">"
    else:
        return "="


def format_bump_table(specs, policy_versions, releases, warnings, ignored_violations):
    table = Table(
        Column("Package", width=20),
        Column("Required", width=8),
        "Required (date)",
        Column("Policy", width=8),
        "Policy (date)",
        "Status",
    )

    heading_style = Style(color="#ff0000", bold=True)
    warning_style = Style(color="#ffff00", bold=True)
    styles = {
        ">": Style(color="#ff0000", bold=True),
        "=": Style(color="#008700", bold=True),
        "<": Style(color="#d78700", bold=True),
    }

    for spec in specs:
        policy_release = policy_versions[spec.name]
        policy_version = policy_release.version.with_segments(0, 2)
        policy_date = policy_release.timestamp

        required_version = spec.version
        required_date = lookup_spec_release(spec, releases).timestamp

        status = version_comparison_symbol(required_version, policy_version)
        if status == ">" and spec.name in ignored_violations:
            style = warning_style
        else:
            style = styles[status]

        table.add_row(
            spec.name,
            str(required_version),
            f"{required_date:%Y-%m-%d}",
            str(policy_version),
            f"{policy_date:%Y-%m-%d}",
            status,
            style=style,
        )

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style=heading_style, vertical="middle")
    grid.add_column()
    grid.add_row("Version summary", table)

    if any(warnings.values()):
        warning_table = Table(width=table.width, expand=True)
        warning_table.add_column("Package")
        warning_table.add_column("Warning")

        for package, messages in warnings.items():
            if not messages:
                continue
            warning_table.add_row(package, messages[0], style=warning_style)
            for message in messages[1:]:
                warning_table.add_row("", message, style=warning_style)

        grid.add_row("Warnings", warning_table)

    return grid


def parse_date(string):
    if not string:
        return None

    return datetime.datetime.strptime(string, "%Y-%m-%d").date()


@click.command()
@click.argument(
    "environment_paths",
    type=click.Path(exists=True, readable=True, path_type=pathlib.Path),
    nargs=-1,
)
@click.option("--today", type=parse_date, default=None)
@click.option("--policy", "policy_file", type=click.File(mode="r"), required=True)
def main(today, policy_file, environment_paths):
    console = Console()

    policy = parse_policy(policy_file)

    parsed_environments = {
        path.stem: parse_environment(path.read_text()) for path in environment_paths
    }

    warnings = {
        env: dict(warnings_) for env, (_, warnings_) in parsed_environments.items()
    }
    environments = {
        env: [spec for spec in specs if spec.name not in policy.exclude]
        for env, (specs, _) in parsed_environments.items()
    }

    all_packages = list(
        dict.fromkeys(spec.name for spec in concat(environments.values()))
    )

    gateway = Gateway()
    query = gateway.query(
        policy.channels, policy.platforms, all_packages, recursive=False
    )
    records = asyncio.run(query)

    if today is None:
        today = datetime.date.today()
    package_releases = pipe(
        records,
        concat,
        group_packages,
        curry(filter_releases, lambda r: r.timestamp is not None),
        deduplicate_releases,
    )
    policy_versions = pipe(
        package_releases,
        curry(find_policy_versions, policy, today),
    )
    status = compare_versions(environments, policy_versions, policy.ignored_violations)

    release_lookup = {
        n: {r.version: r for r in releases} for n, releases in package_releases.items()
    }
    grids = {
        env: format_bump_table(
            specs,
            policy_versions,
            release_lookup,
            warnings[env],
            policy.ignored_violations,
        )
        for env, specs in environments.items()
    }
    root_grid = Table.grid()
    root_grid.add_column()

    for env, grid in grids.items():
        root_grid.add_row(Panel(grid, title=env, expand=True))

    console.print(root_grid)

    status_code = 1 if any(status.values()) else 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()
