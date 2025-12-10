import pathlib

import yaml
from rattler import Version

from minimum_versions.environments.spec import Spec


def parse_spec(spec_text):
    warnings = []
    if ">" in spec_text or "<" in spec_text:
        warnings.append(
            f"package must be pinned with an exact version: {spec_text!r}."
            " Using the version as an exact pin instead."
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

    return Spec(name, version), (name, warnings)


def parse_conda_environment(path: pathlib.Path, manifest_path: None):
    env = yaml.safe_load(pathlib.Path(path).read_text())

    specs = []
    warnings = []
    for dep in env["dependencies"]:
        spec, warnings_ = parse_spec(dep)

        specs.append(spec)
        warnings.append(warnings_)

    return specs, warnings
