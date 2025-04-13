#!/usr/bin/env python3

import time
import datetime
import Adafruit_DHT

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# Ustawienia czujnika DHT
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4  # GPIO4 (pin fizyczny 7) - dostosuj do swojej konfiguracji

# Inicjalizacja I2C i wyświetlacza SSD1306 128x32
serial = i2c(port=1, address=0x3C)  # Zmień adres, jeśli u Ciebie jest inny (np. 0x3D)
device = ssd1306(serial, width=128, height=32)

# Ładujemy czcionkę TrueType (lub None, by użyć wbudowanej)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)

def main():
    try:
        while True:
            # Aktualny czas
            now = datetime.datetime.now()

            # Sprawdzamy, czy to pełna minuta (sekunda == 0)
            # Jeśli tak, pokaż temperaturę przez 1 sekundę
            if now.second == 0:
                humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
                
                with canvas(device) as draw:
                    if temperature is not None:
                        # Wyświetlamy temperaturę
                        temp_str = "Temp: {:.1f} C".format(temperature)
                        draw.text((0, 0), temp_str, font=font, fill=255)
                    else:
                        # Jeśli odczyt się nie udał
                        draw.text((0, 0), "Brak odczytu", font=font, fill=255)
                
                time.sleep(1)  # Czekamy 1 sekundę na wyświetlenie temperatury
            
            else:
                # W pozostałych przypadkach (sekundy != 0) wyświetlamy aktualny czas
                current_time_str = now.strftime('%H:%M:%S')
                with canvas(device) as draw:
                    draw.text((0, 0), current_time_str, font=font, fill=255)
                
                time.sleep(1)  # Odświeżamy co 1 sekundę

    except KeyboardInterrupt:
        # Jeśli przerwiemy program (Ctrl+C), czyścimy wyświetlacz
        device.clear()
        print("Zakończono działanie programu.")

if __name__ == "__main__":
    main()
