# Multi-stage build for ServerObserver
# Stage 1: Build environment
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    libzstd-dev \
    zlib1g-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy the entire repository (needed for Python package)
COPY . /build/

# Install Python package and dependencies in a virtual environment
# This ensures all Python dependencies are bundled
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the conflict_interface package with all its dependencies
# Use the tools-server-observer extra to get httpx with socks support
RUN pip install ".[tools-server-observer]"

# Build the C++ application
WORKDIR /build/tools/server_observer
RUN mkdir -p build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DPYTHON_EXECUTABLE=/opt/venv/bin/python \
          -DBUILD_TESTS=OFF \
          .. && \
    make -j$(nproc)

# Stage 2: Runtime environment
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libzstd1 \
    zlib1g \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy the built executable
COPY --from=builder /build/tools/server_observer/build/server_observer /usr/local/bin/

# Set environment variables for Python
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV PYTHONUNBUFFERED=1

# Create working directory for config files
WORKDIR /app

# Default command
CMD ["server_observer"]
