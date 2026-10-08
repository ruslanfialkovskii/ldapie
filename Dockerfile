# Use Python 3.12 slim as base image
FROM python:3.12-slim

# Add metadata
LABEL maintainer="LDAPie Project"
LABEL description="Modern LDAP client command-line interface tool inspired by HTTPie"
LABEL org.opencontainers.image.source="https://github.com/ruslanfialkovskii/ldapie"

# Build from a throwaway directory; ldap3 is pure Python, so no system packages are needed
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir . && rm -rf /build

# Run as an unprivileged user (home directory is needed for the shell history file)
RUN useradd --create-home ldapie
USER ldapie
WORKDIR /home/ldapie

# Set the entrypoint to the installed console script
ENTRYPOINT ["ldapie"]

# Default command (can be overridden)
CMD ["--help"]
