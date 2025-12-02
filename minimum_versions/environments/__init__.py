import pathlib

from minimum_versions.environments.conda import parse_conda_environment
from minimum_versions.environments.pixi import parse_pixi_environment
from minimum_versions.environments.spec import Spec, compare_versions  # noqa: F401

kinds = {
    "conda": parse_conda_environment,
    "pixi": parse_pixi_environment,
}


def parse_environment(specifier: str, manifest_path: pathlib.Path | None) -> list[Spec]:
    split = specifier.split(":", maxsplit=1)
    if len(split) == 1:
        kind = "conda"
        path = specifier
    else:
        kind, path = split

    parser = kinds.get(kind)
    if parser is None:
        raise ValueError(f"Unknown kind {kind!r}, extracted from {specifier!r}.")

    return parser(path, manifest_path)
