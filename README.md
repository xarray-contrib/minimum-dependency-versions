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

if there are no packages with `overrides`, `exclude`, or `ignored_violations`, you can set
them to an empty dictionary or list, respectively:

```yaml
  ...
  overrides: {}
  exclude: []
  ignored_violations: []
```

then add a new step to CI:

```yaml
jobs:
  my-job:
    ...
    steps:
    ...
    - uses: xarray-contrib/minimum-dependency-versions@version
      with:
        policy: policy.yaml
        environment-paths: path/to/env.yaml
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
        environment-paths: |
          path/to/env1.yaml
          path/to/env2.yaml
          path/to/env3.yaml
```
