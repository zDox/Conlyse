FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    libpq-dev \
    libzstd-dev \
    libxml2-dev \
    curl \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY . /build/

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir ./libs/conflict_interface

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build/services/server_observer
RUN cargo build --release

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libssl3 \
    libpq5 \
    libzstd1 \
    libxml2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/services/server_observer/target/release/server_observer /usr/local/bin/server_observer

ENV PATH="/opt/venv/bin:${PATH}"
ENV VIRTUAL_ENV="/opt/venv"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

CMD ["server_observer"]
