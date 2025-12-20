# xarray-minimum-dependency-versions

Check that the minimum dependency versions follow `xarray`'s policy rules.

> [!NOTE]
> Be aware that at the moment there is no public python API, so there are no
> stability guarantees.

## Policy files

Before we can validate environments we need to create a policy file (named e.g. `policy.yaml`). This allows us to specify the conda channels, the platforms we want to check on, the actual support windows, any overrides, packages that are not supposed to be checked, and allowed violations.

These windows are checked according to `xarray`'s policy, that is, _a version can be required as soon as it is at least N months old_. As opposed to a fixed support window this means we can never end up requiring a one-month old dependency (or being able to drop all existing versions) for packages with infrequent releases.

For example:

```yaml
channels:
  - conda-forge
platforms:
  - noarch
  - linux-64
policy:
  # policy in months
  # Example is xarray's values
  packages:
    python: 30
    numpy: 18
  default: 12
  overrides:
    # override the policy for specific packages
    package3: 0.3.1
  # these packages are completely ignored
  exclude:
    - package1
    - package2
    - ...
  # these packages don't fail the CI, but will be printed in the report as a warning
  ignored_violations:
    - package4
```

If there are no packages with `overrides`, `exclude`, or `ignored_violations`,
you can set them to an empty mapping or sequence, respectively:

```yaml
  ...
  overrides: {}
  exclude: []
  ignored_violations: []
```

### channels

The names of the conda channels to check. Usually, `conda-forge`.

### platforms

The names of the platforms to check. Usually, `noarch` and `linux-64` are sufficient.

### policy

The main policy definition. `packages` is a mapping of package names to the number of months, with `default` specifying the default for packages that are not in `packages`.

Any package listed in `ignored_violations` will show a warning if the policy is violated, but will not count as an error, and it is possible to force a specific version using `overrides`.

## Usage

With the policy file, we can check environment files. There are currently two kinds supported: `conda` environment definitions as yaml files, and `pixi` environments.

Check also `minimum-versions --help` and `minimum-versions validate --help`.

### conda

To validate a `conda` environment file, run:

```sh
minimum-versions validate --policy ./policy.yaml path/to/env1.yaml
```

or with an explicit prefix

```sh
minimum-versions validate --policy ./policy.yaml conda:path/to/env1.yaml
```

We can also validate multiple files at the same time:

```sh
minimum-versions validate --policy .../policy.yaml .../env1.yaml .../env2.yaml
```

### pixi

To validate `pixi` environments, we need to specify the `manifest-path` (usually either `pyproject.toml` or `pixi.toml`):

```sh
minimum-versions validate --policy ./policy.yaml --manifest-path pixi.toml pixi:test-env
```

where `name` in `pixi:<name>` is the name of the environment.

Again, we can validate multiple environments at once:

```sh
minimum-versions validate --policy ./policy.yaml --manifest-path pixi.toml pixi:test-env1 pixi:test-env2
```

### time travel support

To check how validation would look at a certain point in time, use the `--today` option:

```sh
minimum-versions validate --policy ./policy.yaml ./env1.yaml --today 2025-10-01
```
