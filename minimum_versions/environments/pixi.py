import pathlib
import re
import tomllib

from rattler import Version
from tlz.dicttoolz import get_in, merge

from minimum_versions.environments.spec import Spec

_version_re = r"[0-9]+\.[0-9]+(?:\.[0-9]+|\.\*)?"
version_re = re.compile(f"(?P<version>{_version_re})")
lower_pin_re = re.compile(rf">=(?P<version>{_version_re})$")
tight_pin_re = re.compile(rf">=(?P<lower>{_version_re}),<(?P<upper>{_version_re})")


def parse_spec(name, version_text: str | dict):
    # "*" => None
    # "x.y.*" => "x.y"
    # ">=x.y.0,<x.(y + 1).0" => "x.y" (+ warning)
    # ">=x.y.*" => "x.y" (+ warning)

    if isinstance(version_text, dict):
        version_text = version_text.get("version", "*")

    warnings = []
    if version_text == "*":
        raw_version = None
    elif (match := version_re.match(version_text)) is not None:
        raw_version = match.group("version")
    elif (match := lower_pin_re.match(version_text)) is not None:
        warnings.append(
            f"package must be pinned with an exact version: {version_text!r}."
            " Using the version as an exact pin instead."
        )

        raw_version = match.group("version")
    elif (match := tight_pin_re.match(version_text)) is not None:
        lower_pin = match.group("lower")
        upper_pin = match.group("upper")

        warnings.append(
            f"lower pin {lower_pin!r} and upper pin {upper_pin!r} found."
            " Using the lower pin for now, please convert to the standard x.y.* syntax."
        )

        raw_version = lower_pin
    else:
        raise ValueError(f"Unsupported version spec: {version_text}")

    if raw_version is not None:
        version = Version(raw_version.removesuffix(".*"))
        segments = version.segments()
        if (len(segments) == 3 and segments[2] != [0]) or len(segments) > 3:
            warnings.append(
                f"package should be pinned to a minor version (got {version})"
            )
    else:
        version = raw_version

    return Spec(name, version), (name, warnings)


def parse_pixi_environment(name: str, manifest_path: pathlib.Path | None):
    if manifest_path is None:
        raise ValueError("--manifest-path is required for pixi environments.")

    with manifest_path.open(mode="rb") as f:
        data = tomllib.load(f)

    if manifest_path.name == "pyproject.toml":
        pixi_config = get_in(["tool", "pixi"], data, None)
        if pixi_config is None:
            raise ValueError(
                f"The 'tool.pixi' section is missing from {manifest_path}."
            )
    else:
        pixi_config = data

    environment_definitions = pixi_config.get("environments")
    if environment_definitions is None:
        raise ValueError("Can't find environments in the pixi config.")

    all_features = pixi_config.get("feature", {})

    env = environment_definitions.get(name)
    if env is None:
        raise ValueError(f"Unknown environment: {name}")

    if isinstance(env, list):
        feature_names = env
    elif isinstance(env, dict) and env.keys() - {"features", "no-default-feature"}:
        raise ValueError(
            "Options other than 'features' and 'no-default-feature'"
            f" are not supported. Got {env}."
        )
    elif isinstance(env, dict):
        feature_names = env["features"]
        if not env.get("no-default-feature", False):
            feature_names.insert(0, "default")
    else:
        raise ValueError("unexpected environment type")

    unknown_features = [
        name for name in feature_names if name != "default" and name not in all_features
    ]
    if unknown_features:
        raise ValueError(f"unknown features: {', '.join(unknown_features)}")

    features = [
        (
            get_in([feature, "dependencies"], all_features, {})
            if feature != "default"
            else pixi_config.get("dependencies", [])
        )
        for feature in feature_names
    ]

    local_package_name = get_in(["package", "name"], pixi_config, None)
    pins = {
        name: pin
        for name, pin in merge(features).items()
        # skip the local package, if any
        if name != local_package_name
    }

    specs = []
    warnings = []

    pypi_dependencies = {
        feature: (
            get_in([feature, "pypi-dependencies"], all_features)
            if feature != "default"
            else pixi_config.get("pypi-dependencies", [])
        )
        for feature in feature_names
    }
    with_pypi_dependencies = {
        feature: bool(deps) for feature, deps in pypi_dependencies.items() if deps
    }
    for feature in with_pypi_dependencies:
        warnings.append((f"feature:{feature}", ["Ignored PyPI dependencies."]))
    for package_name, pin in pins.items():
        try:
            spec, warnings_ = parse_spec(package_name, pin)
        except ValueError as e:
            e.add_note(f"environment {name}: {package_name}{pin}")
            raise

        specs.append(spec)
        warnings.append(warnings_)

    return specs, warnings
