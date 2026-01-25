#!/bin/bash
# Test IdlerGear in containerized environments
# Usage: ./scripts/podman-test.sh [install|build|matrix]

set -e

# Detect container runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
else
    echo "Error: Neither podman nor docker found. Install one to continue."
    exit 1
fi

echo "Using container runtime: $RUNTIME"

# Get project root (script is in scripts/ directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Function to test installation
test_install() {
    local python_version="${1:-3.11}"
    echo ""
    echo "=========================================="
    echo "Testing installation with Python ${python_version}"
    echo "=========================================="

    $RUNTIME build \
        --build-arg PYTHON_VERSION="${python_version}" \
        -f containers/test-install.Containerfile \
        -t "idlergear-test-install:py${python_version}" \
        .

    echo "✅ Installation test passed for Python ${python_version}"
}

# Function to test build
test_build() {
    local python_version="${1:-3.11}"
    echo ""
    echo "=========================================="
    echo "Testing build with Python ${python_version}"
    echo "=========================================="

    $RUNTIME build \
        --build-arg PYTHON_VERSION="${python_version}" \
        -f containers/test-build.Containerfile \
        -t "idlergear-test-build:py${python_version}" \
        .

    echo "✅ Build test passed for Python ${python_version}"
}

# Function to run full test matrix
test_matrix() {
    echo ""
    echo "=========================================="
    echo "Running full test matrix"
    echo "=========================================="

    local python_versions=("3.10" "3.11" "3.12")

    for version in "${python_versions[@]}"; do
        test_install "$version"
        test_build "$version"
    done

    echo ""
    echo "=========================================="
    echo "✅ All tests passed!"
    echo "=========================================="
}

# Main command dispatch
case "${1:-help}" in
    install)
        test_install "${2:-3.11}"
        ;;
    build)
        test_build "${2:-3.11}"
        ;;
    matrix)
        test_matrix
        ;;
    help|--help|-h)
        echo "Usage: $0 [install|build|matrix] [python_version]"
        echo ""
        echo "Commands:"
        echo "  install [VERSION]  - Test installation (default: Python 3.11)"
        echo "  build [VERSION]    - Test build process (default: Python 3.11)"
        echo "  matrix             - Run full test matrix (Python 3.10, 3.11, 3.12)"
        echo ""
        echo "Examples:"
        echo "  $0 install          # Test install with Python 3.11"
        echo "  $0 install 3.12     # Test install with Python 3.12"
        echo "  $0 build            # Test build with Python 3.11"
        echo "  $0 matrix           # Run all tests"
        ;;
    *)
        echo "Error: Unknown command '${1}'"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
