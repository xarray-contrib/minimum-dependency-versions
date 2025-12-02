from dataclasses import dataclass

from rattler import Version


@dataclass
class Spec:
    name: str
    version: Version | None


def compare_versions(environments, policy_versions, ignored_violations):
    status = {}
    for env, specs in environments.items():
        env_status = any(
            (
                spec.name not in ignored_violations
                and (
                    spec.version is None
                    or spec.version > policy_versions[spec.name].version
                )
            )
            for spec in specs
        )
        status[env] = env_status
    return status
