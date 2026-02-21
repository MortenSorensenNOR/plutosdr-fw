# Build HDL first
cd hdl/project/pluto
export VIVADO_SETTINGS=/opt/Xilinx/Vivado/2024.2/settings64.sh
export ADI_IGNORE_VERSION_CHECK=1
make

# Build podman container image
cd plutosdr-fw
podman build -t plutosdr-build .

# Build firmware
podman run -it --rm -v $(pwd):/build:Z -w /build plutosdr-build bash

## Inside podman
make XSA_FILE=prebuilt_bitstreams/pluto.xsa
