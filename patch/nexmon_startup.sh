#!/bin/bash

# IMPORTANT: Use absolute path instead of $USER
cd /home/chatlxrd/NetStark/patch/nexmon || exit 1

# Source environment
source setup_env.sh

# Build Nexmon top-level
make

# Move into the right patch directory
cd patches/bcm43430a1/7_45_41_46/nexmon/ || exit 1

# Build and install the patched firmware
make
make install-firmware

exit 0
