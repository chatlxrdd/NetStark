import os
import subprocess
import sys
import json

def is_root():
    return os.geteuid() == 0

def get_wifi_interface():
    try:
        result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if 'Interface' in line:
                return line.split()[-1]
    except subprocess.CalledProcessError:
        print("Błąd: Nie można pobrać listy interfejsów WiFi")
        sys.exit(1)
    return None

def is_monitor_mode(interface):
    try:
        result = subprocess.run(['iw', 'dev', interface, 'info'], 
                              capture_output=True, text=True, check=True)
        return 'type monitor' in result.stdout
    except subprocess.CalledProcessError:
        return False


def change_interface_mode(interface, mode):
    try:
        subprocess.run(['ip', 'link', 'set', interface, 'down'], check=True)
        subprocess.run(['iw', 'dev', interface, 'set', 'type', mode], check=True)
        subprocess.run(['ip', 'link', 'set', interface, 'up'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error changing mode: {e}")
        return False

def parse_scan_results(scan_output):
    networks = []
    current_network = {}
    for line in scan_output.split('\n'):
        line = line.strip()
        if line.startswith('BSS'):
            if current_network:
                networks.append(current_network)
            current_network = {'bssid': line.split()[1]}
        elif 'SSID:' in line and current_network:
            current_network['ssid'] = line.split('SSID:', 1)[1].strip()
        elif 'signal:' in line and current_network:
            signal = line.split('signal:', 1)[1].strip()
            current_network['signal'] = signal
        elif 'freq:' in line and current_network:
            freq = line.split('freq:', 1)[1].strip()
            current_network['frequency'] = freq
        elif 'primary channel:' in line and current_network:
            channel = line.split('primary channel:', 1)[1].strip()
            current_network['channel'] = channel
    
    if current_network:
        networks.append(current_network)
    
    return networks
    
def scan_networks(interface):
    subprocess.run(['ip', 'link', 'set', interface, 'up'], check=False)
    
    try:
        result = subprocess.run(['iw', 'dev', interface, 'scan'], 
                              capture_output=True, text=True, check=True, timeout=30)
        return parse_scan_results(result.stdout)
    except subprocess.TimeoutExpired:
    
        print("Error Timeout")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Scannin Error: {e}")
        return []

def save_scan_results_as_json(results, filename):
    with open(filename, 'w') as f:
        json.dump(results, f, indent=4)

def disable_monitor_mode(interface):
    return change_interface_mode(interface, 'managed')

def main():
    if not is_root():
        print("This script must be run as root.")
        sys.exit(1)

    interface = get_wifi_interface()
    if not interface:
        print("No WiFi interface found.")
        sys.exit(1)

    print(f"Using interface: {interface}")

    if not is_monitor_mode(interface):
        print("Switching to monitor mode...")
        if not change_interface_mode(interface, 'monitor'):
            print("Failed to switch to monitor mode.")
            sys.exit(1)

    print("Scanning for WiFi networks...")
    networks = scan_networks(interface)
    if networks:
        print(f"Found {len(networks)} networks.")
        save_scan_results(networks, 'wifi_scan_results.txt')
        print("Scan results saved to wifi_scan_results.txt")
    else:
        print("No networks found.")

    print("Disabling monitor mode...")
    if not disable_monitor_mode(interface):
        print("Failed to disable monitor mode.")
        sys.exit(1)

    print("Done.")