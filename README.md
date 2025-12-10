# minimum-dependency-versions

Check that the minimum dependency versions follow `xarray`'s policy.

## Usage

To use the `minimum-dependency-versions` action in workflows, create a policy file (`policy.yaml`):

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

If there are no packages with `overrides`, `exclude`, or `ignored_violations`, you can set
them to an empty mapping or sequence, respectively:

```yaml
  ...
  overrides: {}
  exclude: []
  ignored_violations: []
```

Then add a new step to CI.

### conda

To analyze conda environments, simply pass the path to the environment file (`env.yaml`) to the `environments` key.

The conda environment file _must_ specify exactly the `conda-forge` channel.

```yaml
jobs:
  my-job:
    ...
    steps:
    ...
    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        policy: policy.yaml
        environments: path/to/env.yaml
```

To analyze multiple environments at the same time, pass a multi-line string:

```yaml
jobs:
  my-job:
    ...
    steps:
    ...

    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        environments: |
          path/to/env1.yaml
          path/to/env2.yaml
          conda:path/to/env3.yaml  # the conda: prefix is optional
```

### pixi

To analyze pixi environments, specify the environment name prefixed with `pixi:` and point to the manifest file using `manifest-path`.

Any environment must pin the dependencies, which must be exact pins (i.e. `x.y.*` or `>=x.y.0,<x.(y + 1).0`, with the former being strongly encouraged). Lower pins are interpreted as exact pins, while all other forms of pinning are not allowed.

```yaml
jobs:
  my-job:
    ...
    steps:
    ...

    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        environments: pixi:env1
        manifest-path: /path/to/pixi.toml  # or pyproject.toml
```

Multiple environments can be analyzed at the same time:

```yaml
jobs:
  my-job:
    ...
    steps:
    ...

    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        environments: |
          pixi:env1
          pixi:env2
        manifest-path: /path/to/pixi.toml  # or pyproject.toml
```

### Mixing environment types

It is even possible to mix environment types (once again, the `conda:` prefix is optional but recommended):

```yaml
jobs:
  my-job:
    ...
    steps:
    ...

    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        environments: |
          pixi:env1
          conda:path/to/env.yaml
        manifest-path: path/to/pixi.toml  # or pyproject.toml
```
