#!/bin/bash
# sync.sh — Push local code to the Raspberry Pi
# Usage: ./sync.sh [file_or_dir...]
#   ./sync.sh                    # sync entire project
#   ./sync.sh pluto/test/test_packet_loss.py   # sync one file

REMOTE="radiotester@100.114.51.4"
REMOTE_DIR="~/plutosdr_fw"

if [ $# -eq 0 ]; then
    rsync -avz  ./build/pluto.dfu "$REMOTE:$REMOTE_DIR/"
    rsync -avz  ./custom_firmware "$REMOTE:$REMOTE_DIR/"
    rsync -avz ./setup_env.sh "$REMOTE:$REMOTE_DIR/"
    rsync -avz ./upload_and_test.sh "$REMOTE:$REMOTE_DIR/"
else
    for f in "$@"; do
        rsync -avz "$f" "$REMOTE:$REMOTE_DIR/$f"
    done
fi

