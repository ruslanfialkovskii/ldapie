# LDAPie Release Process

This document describes the release process for LDAPie.

## Overview

LDAPie uses a GitHub Actions workflow to automate the release process. The workflow handles:

- Version validation and incrementation
- Updating version numbers in code
- Running tests to ensure release quality
- Creating a GitHub release with release notes
- Publishing to PyPI
- Building and pushing Docker images for multiple platforms

## One-Time Setup

### PyPI Trusted Publishing

The workflow publishes to PyPI with [Trusted Publishing](https://docs.pypi.org/trusted-publishers/):
PyPI accepts the OIDC token of the `publish-package` job, so no API token is
stored in the repository secrets. Until the publisher is registered on PyPI,
the publish step fails with "invalid-publisher".

Register it once, on PyPI under the `ldapie` project, **Publishing** →
**Add a new publisher** → **GitHub**:

| Field | Value |
|-------|-------|
| Owner | `ruslanfialkovskii` |
| Repository name | `ldapie` |
| Workflow name | `release.yml` |
| Environment name | `PyPI` |

The `PyPI` environment must exist in the GitHub repository settings
(**Settings** → **Environments**); it already protects the publish job. The
old `PYPI_API_TOKEN` secret is no longer read and can be deleted.

### Docker Hub

`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (an access token with write
permission) stay as repository secrets; Docker Hub has no OIDC equivalent.

## Creating a Release

To create a new release:

1. Go to the GitHub repository Actions tab
2. Select the "LDAPie Release Workflow (Improved)" workflow
3. Click "Run workflow"
4. Configure the release with the following options:

### Release Options

| Option | Description |
|--------|-------------|
| Release Type | Choose from `patch`, `minor`, or `major` to determine how to increment the version number |
| Version | (Optional) Specify an exact version number instead of using automatic incrementation |
| Pre-release | Mark this release as a pre-release if it's not ready for production |
| Draft | Create as a draft release which won't notify users until published |
| Changelog Message | (Optional) Custom message to include in the changelog |

## Release Workflow

The release process executes the following jobs:

1. **Prepare Release**: Determines the new version number, updates version references in code, and creates a Git tag
2. **Test Release**: Runs tests across multiple Python versions against the locked dependencies (`uv.lock`), then installs the package with plain pip as a user would
3. **Build Package**: Creates the Python package for distribution (`uv build`)
4. **Publish to PyPI**: Uploads the package to PyPI through Trusted Publishing
5. **Build Docker Images**: Creates and publishes multi-architecture Docker images, built from the digest-pinned base image and `uv.lock`
6. **Create GitHub Release**: Creates a GitHub release with release notes and artifacts

The actions the workflow uses are pinned to commit SHAs; Dependabot opens pull
requests when new versions are available.

## Accessing Releases

After release, the package can be installed using:

```bash
pip install ldapie==VERSION
```

And the Docker image can be pulled with:

```bash
docker pull ruslanfialkovsky/ldapie:VERSION
```

## Troubleshooting

If a release fails, check the GitHub Actions logs for detailed error information. Common issues include:

- Failed tests
- Version number conflicts
- PyPI rejecting the publish ("invalid-publisher"): the trusted publisher is not registered, or its owner, repository, workflow file name or environment name do not match the table above
- Missing Docker Hub credentials
- Inadequate permissions

For assistance with release issues, contact the project maintainers.
