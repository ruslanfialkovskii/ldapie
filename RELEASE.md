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
- Sending notifications

## Creating a Release

To create a new release:

1. Go to the GitHub repository Actions tab
2. Select the "LDAPie Release Workflow" workflow
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
2. **Test Release**: Runs tests across multiple Python versions to ensure release quality
3. **Build Package**: Creates the Python package for distribution
4. **Publish to PyPI**: Uploads the package to PyPI
5. **Build Docker Images**: Creates and publishes multi-architecture Docker images
6. **Create GitHub Release**: Creates a GitHub release with release notes and artifacts
7. **Send Notifications**: Notifies team members about the new release via Slack

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
- Missing credentials for PyPI or DockerHub
- Inadequate permissions

For assistance with release issues, contact the project maintainers.
