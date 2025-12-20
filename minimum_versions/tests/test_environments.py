import io
import pathlib
import textwrap
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


class TestCondaEnvironment:
    @pytest.mark.parametrize(
        ["spec_text", "expected_spec", "expected_warnings"],
        (
            pytest.param(
                "a=3.2", Spec("a", Version("3.2")), [], id="exact-no_warnings"
            ),
            pytest.param(
                "b>=1.1",
                Spec("b", Version("1.1")),
                [
                    "package must be pinned with an exact version: 'b>=1.1'."
                    " Using the version as an exact pin instead."
                ],
                id="lower_bound",
            ),
            pytest.param(
                "b<=4.1",
                Spec("b", Version("4.1")),
                [
                    "package must be pinned with an exact version: 'b<=4.1'."
                    " Using the version as an exact pin instead."
                ],
                id="upper_equal_bound",
            ),
            pytest.param(
                "b<4.1",
                Spec("b", Version("4.1")),
                [
                    "package must be pinned with an exact version: 'b<=4.1'."
                    " Using the version as an exact pin instead."
                ],
                marks=pytest.mark.xfail(
                    reason="exclusive upper bounds are not supported"
                ),
                id="upper_bound",
            ),
            pytest.param(
                "b>4.1",
                Spec("b", Version("4.1")),
                [
                    "package must be pinned with an exact version: 'b>4.1'."
                    " Using the version as an exact pin instead."
                ],
                marks=pytest.mark.xfail(
                    reason="exclusive lower bounds are not supported"
                ),
                id="lower_bound",
            ),
            pytest.param(
                "c=1.6.2",
                Spec("c", Version("1.6.2")),
                ["package should be pinned to a minor version (got 1.6.2)"],
            ),
        ),
    )
    def test_parse_spec(self, spec_text, expected_spec, expected_warnings):
        actual_spec, (actual_name, actual_warnings) = environments.conda.parse_spec(
            spec_text
        )

        assert actual_spec == expected_spec
        assert actual_name == expected_spec.name
        assert actual_warnings == expected_warnings

    def test_parse_environment(self, monkeypatch):
        data = textwrap.dedent(
            """\
            channels:
            - conda-forge
            dependencies:
            - a=1.1
            - b>=3.2
            - c=1.6.5
            """.rstrip()
        )
        monkeypatch.setattr(pathlib.Path, "read_text", lambda _: data)

        expected_specs = [
            Spec("a", Version("1.1")),
            Spec("b", Version("3.2")),
            Spec("c", Version("1.6.5")),
        ]
        expected_warnings = [
            ("a", []),
            (
                "b",
                [
                    "package must be pinned with an exact version: 'b>=3.2'."
                    " Using the version as an exact pin instead."
                ],
            ),
            ("c", ["package should be pinned to a minor version (got 1.6.5)"]),
        ]

        actual_specs, actual_warnings = environments.conda.parse_conda_environment(
            "env1.yaml", None
        )

        assert actual_specs == expected_specs
        assert actual_warnings == expected_warnings


class TestPixiEnvironment:
    @pytest.mark.parametrize(
        ["name", "version_text", "expected_spec", "expected_warnings"],
        (
            pytest.param(
                "a", "1.2.*", Spec("a", Version("1.2")), [], id="star_pin–no_warnings"
            ),
            pytest.param(
                "b",
                ">=3.1",
                Spec("b", Version("3.1")),
                [
                    "package must be pinned with an exact version: '>=3.1'."
                    " Using the version as an exact pin instead."
                ],
                id="lower_pin",
            ),
            pytest.param(
                "c",
                ">=1.6.0,<1.7.0",
                Spec("c", Version("1.6")),
                [
                    "lower pin '1.6.0' and upper pin '1.7.0' found."
                    " Using the lower pin for now, please convert to"
                    " the standard x.y.* syntax."
                ],
                id="tight_pin",
            ),
            pytest.param(
                "d",
                "1.9.1",
                Spec("d", Version("1.9.1")),
                ["package should be pinned to a minor version (got 1.9.1)"],
                id="patch_pin",
            ),
            pytest.param("e", "*", Spec("e", None), [], id="unpinned"),
            pytest.param("f", {"path": "."}, Spec("f", None), [], id="source_package"),
        ),
    )
    def test_parse_spec(self, name, version_text, expected_spec, expected_warnings):
        actual_spec, (actual_name, actual_warnings) = environments.pixi.parse_spec(
            name, version_text
        )

        assert actual_spec == expected_spec
        assert actual_name == name
        assert actual_warnings == expected_warnings

    @pytest.mark.parametrize("version_text", ("~1.3", "^2.1", "<1.1", "<=2025.01"))
    def test_parse_spec_error(self, version_text):
        with pytest.raises(ValueError, match="Unsupported version spec: .*"):
            environments.pixi.parse_spec("package", version_text)

    @pytest.mark.parametrize(
        ["data", "path", "expected_specs", "expected_warnings"],
        (
            pytest.param(
                textwrap.dedent(
                    """\
                    [dependencies]
                    a = "1.0.*"
                    b = "2.2.*"

                    [feature.feature1.dependencies]
                    c = "3.1.*"

                    [environments]
                    env1 = { features = ["feature1"] }
                    """.rstrip()
                ),
                "pixi.toml",
                [
                    Spec("a", Version("1.0")),
                    Spec("b", Version("2.2")),
                    Spec("c", Version("3.1")),
                ],
                [("a", []), ("b", []), ("c", [])],
                id="default-feature",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [dependencies]
                    a = "1.0.*"
                    b = "2.2.*"

                    [feature.feature1.dependencies]
                    c = "3.1.*"

                    [environments]
                    env1 = { features = ["feature1"], no-default-feature = true }
                    """.rstrip()
                ),
                "pixi.toml",
                [Spec("c", Version("3.1"))],
                [("c", [])],
                id="no-default-feature",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [dependencies]
                    a = "1.0.*"

                    [environments]
                    env1 = { features = [] }
                    """.rstrip()
                ),
                "pixi.toml",
                [Spec("a", Version("1.0"))],
                [("a", [])],
                id="missing-features",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [dependencies]
                    a = "1.0.*"

                    [pypi-dependencies]
                    b = "3.2.*"

                    [environments]
                    env1 = { features = [] }
                    """.rstrip()
                ),
                "pixi.toml",
                [Spec("a", Version("1.0"))],
                [("feature:default", ["Ignored PyPI dependencies."]), ("a", [])],
                id="pypi_dependencies-default",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [dependencies]
                    a = "1.0.*"

                    [feature.feat1.pypi-dependencies]
                    b = "3.2.*"

                    [environments]
                    env1 = { features = ["feat1"] }
                    """.rstrip()
                ),
                "pixi.toml",
                [Spec("a", Version("1.0"))],
                [("feature:feat1", ["Ignored PyPI dependencies."]), ("a", [])],
                id="pypi_dependencies-feat1",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [tool.pixi.feature.feature1.dependencies]
                    c = "3.1.*"

                    [tool.pixi.environments]
                    env1 = { features = ["feature1"], no-default-feature = true }
                    """.rstrip()
                ),
                "pyproject.toml",
                [Spec("c", Version("3.1"))],
                [("c", [])],
                id="pyproject",
            ),
            pytest.param(
                textwrap.dedent(
                    """\
                    [package]
                    name = "a"

                    [dependencies]
                    a = { path = "." }

                    [feature.feature1.dependencies]
                    c = "3.1.*"

                    [environments]
                    env1 = { features = ["feature1"] }
                    """.rstrip()
                ),
                "pixi.toml",
                [Spec("c", Version("3.1"))],
                [("c", [])],
                id="local_package",
            ),
        ),
    )
    def test_parse_pixi_environment(
        self, monkeypatch, path, data, expected_specs, expected_warnings
    ):
        monkeypatch.setattr(
            pathlib.Path, "open", lambda _, mode: io.BytesIO(data.encode())
        )

        name = "env1"
        manifest_path = pathlib.Path(path)

        actual_specs, actual_warnings = environments.pixi.parse_pixi_environment(
            name, manifest_path
        )
        assert actual_specs == expected_specs
        assert actual_warnings == expected_warnings
