#!/usr/bin/env python3
# setup_nexmon_pre_reboot.py
import os
import sys
import subprocess

REQUIRED_PKGS = [
    "raspberrypi-kernel-headers", "git", "libgmp3-dev", "gawk",
    "qpdf", "bison", "flex", "make", "autoconf", "libtool", "texinfo"
]
ARMHF_PKGS = [
    "libc6:armhf", "libisl23:armhf", "libmpfr6:armhf",
    "libmpc3:armhf", "libstdc++6:armhf"
]
DEB_URL = "http://archive.raspberrypi.org/debian/pool/main/f/firmware-nonfree/firmware-brcm80211_0.43+rpi6_all.deb"
DEB_FILE = os.path.basename(DEB_URL)

def run(cmd):
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    if os.geteuid() != 0:
        print("ERROR: must be run as root via sudo.")
        sys.exit(1)

    # 1. Update & upgrade
    run(["apt", "update"])
    run(["apt", "upgrade", "-y"])
    run(["apt", "install", "-y", "vim-common"])
    run(["apt", "install", "-y", "xxd"])

    # 2. Install build deps
    run(["apt", "install", "-y"] + REQUIRED_PKGS)

    # 3. Enable armhf and install libs
    run(["dpkg", "--add-architecture", "armhf"])
    run(["apt", "update"])
    run(["apt", "install", "-y"] + ARMHF_PKGS)

    # 4. Download & downgrade firmware
    run(["wget", "-N", DEB_URL])
    run(["apt", "install", "-y", "--allow-downgrades", f"./{DEB_FILE}"])

    # 5. Backup old Cypress firmware and create fresh dir
    if os.path.isdir("/lib/firmware/cypress"):
        run(["mv", "/lib/firmware/cypress", "/lib/firmware/cypress.bak"])
    run(["mkdir", "-p", "/lib/firmware/cypress"])

    # 6. Reboot to apply the downgraded firmware
    print("\n>>> Pre‐reboot steps complete. Rebooting now to apply firmware downgrade…\n")
    run(["reboot"])

if __name__ == "__main__":
    main()
# pi will reboot
