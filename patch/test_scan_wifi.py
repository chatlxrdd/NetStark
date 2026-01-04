#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import json
import sys
import time
from datetime import datetime

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

def scan_networks(interface):
    print(f"Rozpoczynam skanowanie na interfejsie {interface}...")
    
    subprocess.run(['ip', 'link', 'set', interface, 'up'], check=False)
    
    try:
        result = subprocess.run(['iw', 'dev', interface, 'scan'], 
                              capture_output=True, text=True, check=True, timeout=30)
        return parse_scan_results(result.stdout)
    except subprocess.TimeoutExpired:
        print("Błąd: Skanowanie przekroczyło limit czasu")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Błąd skanowania: {e}")
        return []

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

def save_networks(networks, filename=None):
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'/home/chatlxrd/wifi_scan_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'networks': networks
        }, f, indent=2)
    
    print(f"Zapisano {len(networks)} sieci do {filename}")
    return filename

def disable_monitor_mode(interface):
    print(f"Wyłączam tryb monitor na {interface}...")
    
    try:
        # Zatrzymaj interfejs
        subprocess.run(['ip', 'link', 'set', interface, 'down'], check=True)
        
        # Przełącz do trybu managed
        subprocess.run(['iw', 'dev', interface, 'set', 'type', 'managed'], check=True)
        
        # Uruchom interfejs ponownie
        subprocess.run(['ip', 'link', 'set', interface, 'up'], check=True)
        
        print(f"✓ Interfejs {interface} jest teraz w trybie managed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Błąd podczas wyłączania monitor mode: {e}")
        return False

def main():
    interface = sys.argv[1] if len(sys.argv) > 1 else get_wifi_interface()
    
    if not interface:
        print("Błąd: Nie znaleziono interfejsu WiFi")
        sys.exit(1)
    
    print(f"Używam interfejsu: {interface}")
    
    if not is_monitor_mode(interface):
        print("Ostrzeżenie: Interfejs nie jest w trybie monitor. Kontynuuję...")
    
    networks = scan_networks(interface)
    
    if networks:
        save_networks(networks)
        
        print("\nZnalezione sieci:")
        for net in networks:
            ssid = net.get('ssid', '<hidden>')
            signal = net.get('signal', 'N/A')
            channel = net.get('channel', 'N/A')
            print(f"  {ssid:<30} | Siła: {signal:<10} | Kanał: {channel}")
    else:
        print("Nie znaleziono żadnych sieci")
    
    print("\nPrzełączanie do trybu managed...")
    disable_monitor_mode(interface)
    
    print("\nZakończono!")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Błąd: Ten skrypt wymaga uprawnień root. Uruchom z sudo.")
        sys.exit(1)
    
    main()
