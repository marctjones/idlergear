# Test IdlerGear installation in clean environment
# Usage: podman build -f containers/test-install.Containerfile -t idlergear-test-install .

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /test

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY . /test/idlergear

# Test pip install from source
RUN cd /test/idlergear && \
    pip install --no-cache-dir . && \
    idlergear --version

# Verify commands work
RUN idlergear --help && \
    ig --help

# Test initialization
RUN mkdir /test/project && \
    cd /test/project && \
    idlergear init && \
    test -d .idlergear

CMD ["idlergear", "--version"]
