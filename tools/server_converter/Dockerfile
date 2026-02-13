# Multi-stage build for server_converter

FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy only requirements first for better caching
COPY setup.py pyproject.toml README.md ./
COPY conflict_interface ./conflict_interface
COPY tools ./tools

# Install the package with server-converter dependencies
RUN pip install --no-cache-dir --user -e ".[tools-server-converter]"

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 converter && \
    mkdir -p /app /data/hot_storage && \
    chown -R converter:converter /app /data

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/converter/.local

# Copy application code
COPY --chown=converter:converter conflict_interface ./conflict_interface
COPY --chown=converter:converter tools/server_converter ./tools/server_converter

# Switch to app user
USER converter

# Add local bin to PATH
ENV PATH=/home/converter/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["server-converter", "/app/config.json", "-v"]
