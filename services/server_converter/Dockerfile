# Multi-stage build for server_converter

FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy project files needed to build local packages
COPY services/server_converter/README.md ./README.md
COPY libs/conflict_interface ./libs/conflict_interface
COPY services/server_converter ./services/server_converter

# Install conflict-interface and server-converter in editable mode
RUN pip install --user ./libs/conflict_interface && \
    pip install --user ./services/server_converter

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

# Copy application code (optional, for debugging and source visibility)
COPY --chown=converter:converter libs/conflict_interface/conflict_interface ./conflict_interface
COPY --chown=converter:converter services/server_converter/src ./server_converter

# Switch to app user
USER converter

# Add local bin to PATH
ENV PATH=/home/converter/.local/bin:$PATH \
    PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["server-converter", "/app/config.json", "-v"]
