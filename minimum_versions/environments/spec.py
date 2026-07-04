from dataclasses import dataclass

from rattler import Version


@dataclass
class Spec:
    name: str
    version: Version | None


def compare_versions(environments, policy_versions, ignored_violations):
    status = {}
    warnings = {}
    for env, specs in environments.items():
        violations = {
            spec.name: spec.version is None
            or spec.version > policy_versions[spec.name].version
            for spec in specs
        }
        status[env] = any(
            value
            for name, value in violations.items()
            if name not in ignored_violations
        )
        warnings[env] = {
            name: ["violation unnecessarily ignored"]
            for name, value in violations.items()
            if not value and name in ignored_violations
        }

    return status, warnings
