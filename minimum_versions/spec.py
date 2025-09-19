from dataclasses import dataclass

import yaml
from rattler import Version


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


def parse_environment(text):
    env = yaml.safe_load(text)

    specs = []
    warnings = []
    for dep in env["dependencies"]:
        spec, warnings_ = Spec.parse(dep)

        specs.append(spec)
        warnings.append(warnings_)

    return specs, warnings
