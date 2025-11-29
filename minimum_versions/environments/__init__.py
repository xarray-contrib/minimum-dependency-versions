from minimum_versions.environments.conda import parse_conda_environment  # noqa: F401
from minimum_versions.environments.spec import Spec, compare_versions  # noqa: F401

kinds = {
    "conda": parse_conda_environment,
}


def parse_environment(specifier: str) -> list[Spec]:
    kind, path = specifier.split(":", maxsplit=1)

    parser = kinds.get(kind)
    if parser is None:
        raise ValueError(f"Unknown kind {kind!r}, extracted from {specifier!r}.")

    return parser(path)
