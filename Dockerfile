FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libncurses5-dev \
    libssl-dev \
    ccache \
    dfu-util \
    u-boot-tools \
    device-tree-compiler \
    mtools \
    bc \
    python3 \
    cpio \
    zip \
    unzip \
    rsync \
    file \
    wget \
    xz-utils \
    flex \
    bison \
    libgmp-dev \
    libmpc-dev \
    libmpfr-dev \
    git \
    gcc-arm-linux-gnueabihf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
