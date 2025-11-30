import datetime

from rich.style import Style
from rich.table import Column, Table

from minimum_versions.release import Release


def lookup_spec_release(spec, releases):
    version = spec.version.extend_to_length(3)

    compatible_versions = [
        release
        for v, release in releases[spec.name].items()
        if v.compatible_with(version)
    ]
    if not compatible_versions:
        return Release(version="", build_number=0, timestamp=datetime.date(1970, 1, 1))

    return compatible_versions[0]


def version_comparison_symbol(required, policy):
    if required is None:
        return "!"
    elif required < policy:
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
        "!": warning_style,
    }

    for spec in specs:
        policy_release = policy_versions[spec.name]
        policy_version = policy_release.version.with_segments(0, 2)
        policy_date = policy_release.timestamp

        required_version = spec.version
        if required_version is None:
            warnings[spec.name].append(
                "Unpinned dependency. Consider pinning or ignoring this dependency."
            )
            required_date = None
        else:
            required_date = lookup_spec_release(spec, releases).timestamp

        status = version_comparison_symbol(required_version, policy_version)
        if status == ">" and spec.name in ignored_violations:
            style = warning_style
        else:
            style = styles[status]

        table.add_row(
            spec.name,
            str(required_version) if required_version is not None else "",
            f"{required_date:%Y-%m-%d}" if required_date is not None else "",
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
