#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
import time
import logging
import subprocess

picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button

logging.basicConfig(level=logging.INFO, filename='/var/log/epaper.log')

# GPIO BCM
BTN_SELECT_PIN = 5
BTN_UP_PIN     = 6
BTN_DOWN_PIN   = 13

menu_items = [
    "Scan WiFi",
    "Deauth",
    "Injection",
    "Power Off",  # NOWE: wyłącza Pi
]

current_index = 0
epd = None
font_item = None
screen_state = "splash"  # splash -> menu

def show_splash():
    """Pokazuje bitmapę na start"""
    global epd
    logging.info("Showing splash bitmap...")
    epd.init()
    epd.Clear(0xFF)
    
    # Twoja bitmapa (dostosuj nazwę)
    splash_image = Image.open(os.path.join(picdir, '2in13.bmp'))  # lub swoją
    epd.display(epd.getbuffer(splash_image))
    time.sleep(3)  # 3s splash

def clear_screen():
    """Czyści ekran przy wyłączaniu"""
    global epd
    epd.init()
    epd.Clear(0xFF)
    epd.sleep()
    logging.info("Screen cleared")

def draw_menu_image(index):
    """Rysuje menu z zaznaczeniem"""
    global epd, font_item
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    font_title = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
    draw.text((10, 5), "Menu", font=font_title, fill=0)

    y = 35
    for i, item in enumerate(menu_items):
        prefix = "> " if i == index else "  "
        draw.text((10, y), prefix + item, font=font_item, fill=0)
        y += 18

    return image

def power_off():
    """Wyłącza Raspberry Pi"""
    logging.info("Powering off...")
    clear_screen()
    time.sleep(1)
    subprocess.run(['sudo', 'poweroff'])

def main():
    global epd, font_item, current_index, screen_state
    try:
        epd = epd2in13_V4.EPD()
        font_item = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)

        # SPLASH na start
        show_splash()
        
        # Przejdź do menu
        screen_state = "menu"
        current_index = 0
        image = draw_menu_image(0)
        epd.display(epd.getbuffer(image))

        # Przyciski
        btn_select = Button(BTN_SELECT_PIN, pull_up=True, bounce_time=0.2)
        btn_up     = Button(BTN_UP_PIN,     pull_up=True, bounce_time=0.2)
        btn_down   = Button(BTN_DOWN_PIN,   pull_up=True, bounce_time=0.2)

        def on_up():
            current_index = (current_index - 1) % len(menu_items)
            image = draw_menu_image(current_index)
            epd.displayPartial(epd.getbuffer(image))
            logging.info("Menu: %s", menu_items[current_index])

        def on_down():
            current_index = (current_index + 1) % len(menu_items)
            image = draw_menu_image(current_index)
            epd.displayPartial(epd.getbuffer(image))
            logging.info("Menu: %s", menu_items[current_index])

        def on_select():
            selected = menu_items[current_index]
            logging.info("Selected: %s", selected)
            
            if selected == "Power Off":
                power_off()
            # Tutaj dodaj inne akcje: WiFi scan, etc.

        btn_up.when_pressed = on_up
        btn_down.when_pressed = on_down
        btn_select.when_pressed = on_select

        # Główna pętla
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        clear_screen()
    finally:
        epd2in13_V4.epdconfig.module_exit(cleanup=True)

if __name__ == "__main__":
    main()
