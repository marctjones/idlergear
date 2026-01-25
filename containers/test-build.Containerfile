# Test IdlerGear build process in clean environment
# Usage: podman build -f containers/test-build.Containerfile -t idlergear-test-build .

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install build tools
RUN pip install --no-cache-dir build twine

# Copy source
COPY . /build/idlergear

# Test build process
RUN cd /build/idlergear && \
    python -m build && \
    ls -lh dist/

# Validate wheel and sdist
RUN cd /build/idlergear && \
    twine check dist/*

# Test wheel installation
RUN cd /build/idlergear && \
    pip install dist/*.whl && \
    idlergear --version

CMD ["ls", "-lh", "/build/idlergear/dist/"]
