import datetime
import os.path
import pathlib
import sys
from typing import Any

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tlz.itertoolz import concat, unique

from minimum_versions.environments import compare_versions, parse_environment
from minimum_versions.formatting import format_bump_table
from minimum_versions.policy import find_policy_versions, parse_policy
from minimum_versions.release import fetch_releases

click.rich_click.SHOW_ARGUMENTS = True


def parse_date(string):
    if not string:
        return None

    return datetime.datetime.strptime(string, "%Y-%m-%d").date()


class _Path(click.Path):
    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> Any:
        if not value:
            return None

        return super().convert(value, param, ctx)


@click.group()
def main():
    pass


@main.command()
@click.argument("environment_paths", type=str, nargs=-1)
@click.option(
    "--manifest-path",
    "manifest_path",
    type=_Path(exists=True, path_type=pathlib.Path),
    default=None,
)
@click.option("--today", type=parse_date, default=None)
@click.option("--policy", "policy_file", type=click.File(mode="r"), required=True)
def validate(today, policy_file, manifest_path, environment_paths):
    console = Console()

    policy = parse_policy(policy_file)

    parsed_environments = {
        path.rsplit(os.path.sep, maxsplit=1)[-1]: parse_environment(path, manifest_path)
        for path in environment_paths
    }

    warnings = {
        env: dict(warnings_) for env, (_, warnings_) in parsed_environments.items()
    }
    environments = {
        env: [spec for spec in specs if spec.name not in policy.exclude]
        for env, (specs, _) in parsed_environments.items()
    }

    all_packages = list(
        unique(
            spec.name
            for spec in concat(environments.values())
            if spec.name not in policy.exclude
        )
    )

    package_releases = fetch_releases(policy.channels, policy.platforms, all_packages)

    if today is None:
        today = datetime.date.today()

    policy_versions = find_policy_versions(policy, today, package_releases)

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
