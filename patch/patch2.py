#!/usr/bin/env python3
# setup_nexmon_post_reboot.py
import os
import sys
import subprocess

NEXMON_REPO = "https://github.com/thau0x01/nexmon.git"
PATCH_SUBDIR = "patches/bcm43430a1/7_45_41_46/nexmon"
LINKS = [
    ("/usr/lib/arm-linux-gnueabihf/libisl.so.23.2.0",
     "/usr/lib/arm-linux-gnueabihf/libisl.so.10"),
    ("/usr/lib/arm-linux-gnueabihf/libmpfr.so.6.2.0",
     "/usr/lib/arm-linux-gnueabihf/libmpfr.so.4")
]

def run(cmd):
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    if os.geteuid() != 0:
        print("ERROR: must be run as root via sudo.")
        sys.exit(1)
    # 0. Delete existing symlinks
    run(["rm","-rf","/usr/lib/arm-linux-gnueabihf/libisl.so.23", "|", "rm","-rf","/usr/lib/arm-linux-gnueabihf/libmpfr.so.6")
    # 1. Clone & build core
    if not os.path.isdir("nexmon"):
        run(["git", "clone", NEXMON_REPO])
    os.chdir("nexmon")
    run(["bash", "-c", "source setup_env.sh && make"])

    # 2. Apply patch
    os.chdir(PATCH_SUBDIR)
    for src, dst in LINKS:
        run(["ln", "-sf", src, dst])

    # 3. Build & install firmware patch
    run(["make"])
    run(["make", "install-firmware"])

    print("\n✅ Nexmon patched and firmware installed. You should now see monitor mode in `iw list`.")
    print("The patch will persist across reboots once this is done.")
    
if __name__ == "__main__":
    main()
