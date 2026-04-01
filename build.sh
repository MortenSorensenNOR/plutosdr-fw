#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_HDL=0

usage() {
    echo "Usage: $0 [--hdl]"
    echo "  --hdl    Also build HDL bitstream with Vivado (requires Vivado install)"
    exit 1
}

for arg in "$@"; do
    case $arg in
        --hdl) BUILD_HDL=1 ;;
        *) usage ;;
    esac
done

cd "$SCRIPT_DIR"

if [ $BUILD_HDL -eq 1 ]; then
    echo "==> Building HDL..."
    export VIVADO_SETTINGS=/opt/Xilinx/Vivado/2024.2/settings64.sh
    export ADI_IGNORE_VERSION_CHECK=1
    make -C hdl/projects/pluto
fi

echo "==> Building podman container image..."
podman build -t plutosdr-build .

echo "==> Building firmware..."
podman run --rm -v "$SCRIPT_DIR":/build:Z -w /build plutosdr-build \
    make XSA_FILE=prebuilt_bitstreams/pluto.xsa

echo "==> Done. Firmware at build/pluto.dfu"
