# Use Python 3.9 slim as base image
FROM python:3.9-slim

# Add metadata
LABEL maintainer="LDAPie Project"
LABEL description="Modern LDAP client command-line interface tool inspired by HTTPie"
LABEL org.opencontainers.image.source="https://github.com/username/ldapie"

# Set working directory
WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY src/ src/
COPY ldapie .
COPY completion.zsh .
COPY setup.py .
COPY README.md .
COPY LICENSE .

# Make the ldapie script executable
RUN chmod +x ./ldapie

# Create a symbolic link to make ldapie available in PATH
RUN ln -s /app/ldapie /usr/local/bin/ldapie

# Set the entrypoint to the ldapie script
ENTRYPOINT ["ldapie"]

# Default command (can be overridden)
CMD ["--help"]
