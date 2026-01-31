#!/bin/bash
# Build script for ServerObserver Docker image

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="server-observer"
IMAGE_TAG="latest"
DOCKERFILE_PATH="tools/server_observer/Dockerfile"
BUILD_CONTEXT="."

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -n, --name NAME    Set the image name (default: server-observer)"
            echo "  -t, --tag TAG      Set the image tag (default: latest)"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 --name my-observer --tag v1.0"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Full image name
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

print_info "Building ServerObserver Docker image..."
print_info "Image name: ${FULL_IMAGE_NAME}"
print_info "Dockerfile: ${DOCKERFILE_PATH}"
print_info "Build context: ${BUILD_CONTEXT}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "${DOCKERFILE_PATH}" ]; then
    print_error "Dockerfile not found at ${DOCKERFILE_PATH}"
    exit 1
fi

# Build the Docker image
print_info "Starting Docker build..."
docker build \
    -f "${DOCKERFILE_PATH}" \
    -t "${FULL_IMAGE_NAME}" \
    "${BUILD_CONTEXT}"

# With set -e, we only reach here if the build succeeded
echo ""
print_info "✓ Build completed successfully!"
echo ""
print_info "Image details:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""
print_info "To run the container:"
echo "  docker run -v \$(pwd)/config:/app ${FULL_IMAGE_NAME}"
echo ""
print_info "To run with custom config:"
echo "  docker run -v /path/to/config:/app ${FULL_IMAGE_NAME} server_observer /app/config.json /app/account_pool.json"
