from dataclasses import dataclass

import pytest
from rattler import Version

from minimum_versions import environments
from minimum_versions.environments.spec import Spec


@dataclass
class FakeRecord:
    version: Version | None


@pytest.mark.parametrize("manifest_path", ("a/pixi.toml", "b/pyproject.toml", None))
@pytest.mark.parametrize(
    ["specifier", "key"], (("conda:ci/environment.yml", "conda"), ("pixi:env", "pixi"))
)
def test_parse_environment(specifier, manifest_path, key, monkeypatch):
    results = {"conda": object(), "pixi": object()}
    kinds = {
        "conda": lambda s, m: results["conda"],
        "pixi": lambda s, m: results["pixi"],
    }
    monkeypatch.setattr(environments, "kinds", kinds)

    actual = environments.parse_environment(specifier, manifest_path)
    expected = results[key]

    assert actual is expected


@pytest.mark.parametrize(
    ["envs", "ignored_violations", "expected"],
    (
        pytest.param(
            {
                "env1": [
                    Spec("a", Version("1.2")),
                    Spec("c", Version("2024.8")),
                    Spec("d", Version("0.6")),
                ]
            },
            ["d"],
            {"env1": False},
            id="single-violation-ignored",
        ),
        pytest.param(
            {
                "env1": [Spec("b", Version("3.2")), Spec("c", Version("2025.2"))],
                "env2": [Spec("b", Version("3.1"))],
            },
            [],
            {"env1": True, "env2": False},
            id="multiple-split-not ignored",
        ),
        pytest.param(
            {"env1": [Spec("d", None)]},
            [],
            {"env1": True},
            id="single-none-not ignored",
        ),
        pytest.param(
            {"env1": [Spec("d", None)]},
            ["d"],
            {"env1": False},
            id="single-none-ignored",
        ),
    ),
)
def test_compare_versions(envs, ignored_violations, expected):
    policy_versions = {
        "a": FakeRecord(version=Version("1.2")),
        "b": FakeRecord(version=Version("3.1")),
        "c": FakeRecord(version=Version("2025.1")),
        "d": FakeRecord(version=Version("0.5")),
    }

    actual = environments.spec.compare_versions(
        envs, policy_versions, ignored_violations
    )
    assert actual == expected
