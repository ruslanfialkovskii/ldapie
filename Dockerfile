# Images are pinned by digest so a rebuild of the same tag is the same image;
# Dependabot updates the digests. uv comes from its own image because a FROM
# line is what Dependabot tracks.
FROM ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 AS uv

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS build

COPY --from=uv /uv /bin/uv
WORKDIR /app
# Copy instead of hardlinking across layers, use the image's Python, keep no
# cache, and compile bytecode now: the app user cannot write __pycache__ later
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1 UV_COMPILE_BYTECODE=1

# Dependencies first, exactly as locked, so this layer survives source changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

# Then the package itself (README and LICENSE are part of its metadata)
COPY README.md LICENSE ./
COPY src/ src/
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f

LABEL maintainer="LDAPie Project"
LABEL description="Modern LDAP client command-line interface tool inspired by HTTPie"
LABEL org.opencontainers.image.source="https://github.com/ruslanfialkovskii/ldapie"

# Only the virtual environment is carried over; no build tools, no sources
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Run as an unprivileged user (home directory is needed for the shell history file)
RUN useradd --create-home ldapie
USER ldapie
WORKDIR /home/ldapie

# Set the entrypoint to the installed console script
ENTRYPOINT ["ldapie"]

# Default command (can be overridden)
CMD ["--help"]
