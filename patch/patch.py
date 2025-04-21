#!/usr/bin/env python3
import os
import sys
import subprocess



#The script will reboot your Pi after downgrading the firmware. After reboot, re-run the script (it will skip steps already done) to finish building and installing the Nexmon patch.
# Manual Process: https://github.com/rudyrdx/Raspberry-Pi-Zero-2w/blob/main/Monitor%20Mode.md
REQUIRED_PKGS = [
    "raspberrypi-kernel-headers",
    "git",
    "libgmp3-dev",
    "gawk",
    "qpdf",
    "bison",
    "flex",
    "make",
    "autoconf",
    "libtool",
    "texinfo"
]

ARMHF_PKGS = [
    "libc6:armhf",
    "libisl23:armhf",
    "libmpfr6:armhf",
    "libmpc3:armhf",
    "libstdc++6:armhf"
]

DEB_URL = "http://archive.raspberrypi.org/debian/pool/main/f/firmware-nonfree/firmware-brcm80211_0.43+rpi6_all.deb"
DEB_FILE = "firmware-brcm80211_0.43+rpi6_all.deb"
NEXMON_REPO = "https://github.com/seemoo-lab/nexmon.git"
PATCH_DIR = "patches/bcm43430a1/7_45_41_46/nexmon"

def run(cmd, **kwargs):
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)

def main():
    if os.geteuid() != 0:
        print("This script must be run as root. Try: sudo ./setup_nexmon.py")
        sys.exit(1)

    # 1. Update & Upgrade
    run(["apt", "update"])
    run(["apt", "upgrade", "-y"])

    # 2. Install required packages
    run(["apt", "install", "-y"] + REQUIRED_PKGS)

    # 3. Enable armhf architecture & install libs
    run(["dpkg", "--add-architecture", "armhf"])
    run(["apt", "update"])
    run(["apt", "install", "-y"] + ARMHF_PKGS)

    # 4. Downgrade firmware
    run(["wget", "-N", DEB_URL])
    run(["apt", "install", "-y", "--allow-downgrades", f"./{DEB_FILE}"])
    # Backup and recreate cypress firmware dir
    if os.path.isdir("/lib/firmware/cypress"):
        run(["mv", "/lib/firmware/cypress", "/lib/firmware/cypress.bak"])
    run(["mkdir", "-p", "/lib/firmware/cypress"])

    # 5. Reboot to apply firmware downgrade
    print("Rebooting now to apply firmware downgrade...")
    run(["reboot"])

    # Below lines will only run after manual re-login (or re-run script).

    # 6. Clone nexmon & build core
    if not os.path.isdir("nexmon"):
        run(["git", "clone", NEXMON_REPO])
    os.chdir("nexmon")

    run(["bash", "-c", "source setup_env.sh && make"])

    # 7. Enter patch directory
    os.chdir(PATCH_DIR)

    # 8. Create symlinks for legacy lib versions
    run([
        "ln", "-sf",
        "/usr/lib/arm-linux-gnueabihf/libisl.so.23.0.0",
        "/usr/lib/arm-linux-gnueabihf/libisl.so.10"
    ])
    run([
        "ln", "-sf",
        "/usr/lib/arm-linux-gnueabihf/libmpfr.so.6.1.0",
        "/usr/lib/arm-linux-gnueabihf/libmpfr.so.4"
    ])

    # 9. Build & install firmware patch
    run(["make"])
    run(["make", "install-firmware"])

    print("Nexmon patch installed. You should now see monitor mode support with `iw list`.")
    print("To persist drivers across reboots, re-run `make install-firmware` or set up a boot script.")
    print("Done.")

if __name__ == "__main__":
    main()
