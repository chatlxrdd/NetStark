#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
import time
import logging
import subprocess
import random
import string
from scripts.pentests import scan_wifi, deauth, probe_request_flood, beacon_flood
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
fontsdir = os.path.join(BASE_DIR, 'fonts', 'Font.ttc')
libdir = os.path.join(BASE_DIR, 'lib')

# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
if os.path.exists(libdir):
    sys.path.append(libdir)
from lib.waveshare_epd import epd2in13_V4
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button
import glob, csv

logging.basicConfig(level=logging.INFO, filename='/var/log/epaper.log')

# GPIO BCM
BTN_SELECT_PIN = 5
BTN_UP_PIN     = 6
BTN_DOWN_PIN   = 13

menu_items = [
    "Scan WiFi",
    "Deauth",
    "Probe Request Flood",
    "Beacon Flood",
    "Power Off",
]

current_index = 0
epd = None
font_item = None
screen_state = "splash"  # splash -> menu

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

    font_title = ImageFont.truetype(fontsdir, 16)
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
        font_item = ImageFont.truetype(fontsdir, 12)
        epd.init()

        # SPLASH na start
        # show_splash()
        
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
            global current_index
            current_index = (current_index - 1) % len(menu_items)
            image = draw_menu_image(current_index)
            epd.displayPartial(epd.getbuffer(image))
            logging.info("Menu: %s", menu_items[current_index])

        def on_down():
            global current_index
            current_index = (current_index + 1) % len(menu_items)
            image = draw_menu_image(current_index)
            epd.displayPartial(epd.getbuffer(image))
            logging.info("Menu: %s", menu_items[current_index])

        def on_select(menu_item):
            menu_item = menu_items[current_index]
            logging.info("Selected: %s", menu_item)
            if menu_item == "Scan WiFi":
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Skanowanie WiFi...", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                logging.info("Starting WiFi scan...")
                scan_wifi("wlan0mon")
                # plik CSV znajduje sie w katalogu "data" obok skryptu
                csv_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
                csv_files = glob.glob(os.path.join(csv_dir, '*.csv'))
                if not csv_files:
                    logging.info("Brak plikow CSV w katalogu: %s", csv_dir)
                    image = Image.new('1', (epd.height, epd.width), 255)
                    draw = ImageDraw.Draw(image)
                    draw.text((10, 10), "Brak plikow .csv w data", font=font_item, fill=0)
                    epd.displayPartial(epd.getbuffer(image))
                    time.sleep(2)
                else:
                    latest_csv = max(csv_files, key=os.path.getmtime)
                    logging.info("Wczytywanie CSV: %s", latest_csv)
                    rows = []
                    header = None
                    try:
                        with open(latest_csv, newline='', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            header = next(reader, None)
                            for r in reader:
                                rows.append(r)
                    except Exception as e:
                        logging.exception("Blad podczas czytania CSV")
                        image = Image.new('1', (epd.height, epd.width), 255)
                        draw = ImageDraw.Draw(image)
                        draw.text((10, 10), "Blad odczytu CSV", font=font_item, fill=0)
                        epd.displayPartial(epd.getbuffer(image))
                        time.sleep(2)
                    else:
                        # przygotuj widok listy z nawigacja przyciskami
                        title_font = ImageFont.truetype(os.path.join(fon, 'Font.ttc'), 16)
                        line_height = 14
                        top_y = 30
                        bottom_info = "UP/DOWN: przewijaj  SELECT: powrot"
                        # kolumny, które chcemy wyświetlać
                        desired_cols = ["BSSID", "Channel", "Privacy", "Key"]
                        # stan widoku
                        start_idx = 0
                        cursor = 0
                        # ile linii (wierszy) można wyświetlić na stronie (zostaw miejsce na info)
                        page_height = epd.width - top_y - 18  # 18 na info
                        lines_per_page = max(1, page_height // line_height)

                        # jeśli mamy nagłówek, ustal indeksy dla desired_cols (case-insensitive, dopasowania alternatywne)
                        col_indices = None
                        if header:
                            hdr_lower = [h.strip().lower() for h in header]
                            col_indices = []
                            for col in desired_cols:
                                col_l = col.lower()
                                # możliwe alternatywy (np. chanel -> channel)
                                if col_l == "channel":
                                    candidates = ["channel", "chanel", "chan"]
                                else:
                                    candidates = [col_l]
                                idx = None
                                for c in candidates:
                                    if c in hdr_lower:
                                        idx = hdr_lower.index(c)
                                        break
                                col_indices.append(idx)
                        else:
                            # brak nagłówka -> wybierz pierwsze cztery kolumny
                            col_indices = [i if i < 10000 and i < 1000 else None for i in range(len(desired_cols))]
                            # fallback to sequential indices 0..3
                            col_indices = list(range(min(len(desired_cols), 4)))

                        def draw_csv_view():
                            image = Image.new('1', (epd.height, epd.width), 255)
                            draw = ImageDraw.Draw(image)
                            # tytul
                            draw.text((10, 5), "Scan: " + os.path.basename(latest_csv), font=title_font, fill=0)
                            y = top_y
                            # naglowek stały - pokaz to co użytkownik chciał
                            header_text = " | ".join(desired_cols)
                            draw.text((10, y), header_text[:epd.height//6], font=font_item, fill=0)
                            y += line_height
                            # pokaz widok strony
                            for i in range(start_idx, min(start_idx + lines_per_page, len(rows))):
                                prefix = "> " if i == cursor else "  "
                                row = rows[i]
                                parts = []
                                for ci in col_indices:
                                    val = ""
                                    if isinstance(ci, int) and ci is not None and ci < len(row):
                                        val = row[ci]
                                    parts.append(val)
                                text = " | ".join(parts)
                                # przytnij do rozsadnego rozmiaru
                                max_chars = 40
                                draw.text((10, y), prefix + text[:max_chars], font=font_item, fill=0)
                                y += line_height
                            # dolny srodkowy tekst informacyjny
                            info_w = draw.textsize(bottom_info, font=font_item)[0]
                            info_x = (epd.height - info_w) // 2
                            draw.text((info_x, epd.width - 16), bottom_info, font=font_item, fill=0)
                            epd.displayPartial(epd.getbuffer(image))

                        # zapamietaj stare handlery by przywrocic menu
                        old_up = btn_up.when_pressed
                        old_down = btn_down.when_pressed
                        old_select = btn_select.when_pressed

                        # handlery dla widoku CSV
                        def csv_on_up():
                            nonlocal start_idx, cursor
                            if cursor > 0:
                                cursor -= 1
                            # przesun stronę w górę jeśli kursor wyszedł poza widoczne okno
                            if cursor < start_idx:
                                start_idx = cursor
                            draw_csv_view()
                            logging.info("CSV cursor: %d start: %d", cursor, start_idx)

                        def csv_on_down():
                            nonlocal start_idx, cursor
                            if cursor < len(rows) - 1:
                                cursor += 1
                            # przesun stronę w dol jeśli kursor wyszedl poza widoczne okno
                            if cursor >= start_idx + lines_per_page:
                                start_idx = cursor - lines_per_page + 1
                            draw_csv_view()
                            logging.info("CSV cursor: %d start: %d", cursor, start_idx)

                        def csv_on_select():
                            # przywróć poprzednie handlery (powrót do menu)
                            btn_up.when_pressed = old_up
                            btn_down.when_pressed = old_down
                            btn_select.when_pressed = old_select
                            # narysuj menu ponownie
                            try:
                                image = draw_menu_image(current_index)
                                epd.displayPartial(epd.getbuffer(image))
                                logging.info("Returned to menu from CSV view")
                            except Exception:
                                logging.exception("Error while returning to menu")

                        # ustaw nowe handlery
                        btn_up.when_pressed = csv_on_up
                        btn_down.when_pressed = csv_on_down
                        btn_select.when_pressed = csv_on_select

                        # pokaż pierwszy widok
                        draw_csv_view()
                        logging.info("Wyswietlono zawartosc CSV: %s", latest_csv)
                        
            if menu_item == "Deauth":
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Wczytywanie sieci...", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                
                csv_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
                csv_files = glob.glob(os.path.join(csv_dir, '*.csv'))
                
                if not csv_files:
                    image = Image.new('1', (epd.height, epd.width), 255)
                    draw = ImageDraw.Draw(image)
                    draw.text((10, 10), "Brak plikow .csv w data", font=font_item, fill=0)
                    epd.displayPartial(epd.getbuffer(image))
                    time.sleep(2)
                else:
                    latest_csv = max(csv_files, key=os.path.getmtime)
                    rows = []
                    try:
                        with open(latest_csv, newline='', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            next(reader, None)
                            for r in reader:
                                rows.append(r)
                    except Exception as e:
                        logging.exception("Blad podczas czytania CSV")
                        time.sleep(2)
                        return
                    
                    if not rows:
                        image = Image.new('1', (epd.height, epd.width), 255)
                        draw = ImageDraw.Draw(image)
                        draw.text((10, 10), "Brak sieci WiFi", font=font_item, fill=0)
                        epd.displayPartial(epd.getbuffer(image))
                        time.sleep(2)
                        return
                    
                    old_up = btn_up.when_pressed
                    old_down = btn_down.when_pressed
                    old_select = btn_select.when_pressed
                    
                    wifi_cursor = 0
                    deauth_options = ["Single Network", "Deauth All"] + [rows[i][0] if rows[i] else "?" for i in range(len(rows))]
                    
                    def draw_deauth_menu():
                        image = Image.new('1', (epd.height, epd.width), 255)
                        draw = ImageDraw.Draw(image)
                        draw.text((10, 5), "Deauth mode:", font=font_item, fill=0)
                        y = 25
                        for i in range(min(5, 2)):
                            prefix = "> " if i == wifi_cursor else "  "
                            draw.text((10, y), prefix + deauth_options[i], font=font_item, fill=0)
                            y += 18
                        epd.displayPartial(epd.getbuffer(image))
                    
                    def deauth_menu_up():
                        nonlocal wifi_cursor
                        wifi_cursor = (wifi_cursor - 1) % 2
                        draw_deauth_menu()
                    
                    def deauth_menu_down():
                        nonlocal wifi_cursor
                        wifi_cursor = (wifi_cursor + 1) % 2
                        draw_deauth_menu()
                    
                    def deauth_menu_select():
                        nonlocal wifi_cursor
                        if wifi_cursor == 0:
                            show_wifi_list()
                        else:
                            deauth_all_networks()
                    
                    def show_wifi_list():
                        nonlocal wifi_cursor
                        wifi_cursor = 0
                        
                        def draw_wifi_list():
                            image = Image.new('1', (epd.height, epd.width), 255)
                            draw = ImageDraw.Draw(image)
                            draw.text((10, 5), "Wybierz siec:", font=font_item, fill=0)
                            y = 25
                            for i in range(min(5, len(rows))):
                                prefix = "> " if i == wifi_cursor else "  "
                                ssid = rows[i][0] if rows[i] else "?"
                                draw.text((10, y), prefix + ssid[:20], font=font_item, fill=0)
                                y += 18
                            epd.displayPartial(epd.getbuffer(image))
                        
                        def wifi_up():
                            nonlocal wifi_cursor
                            wifi_cursor = (wifi_cursor - 1) % len(rows)
                            draw_wifi_list()
                        
                        def wifi_down():
                            nonlocal wifi_cursor
                            wifi_cursor = (wifi_cursor + 1) % len(rows)
                            draw_wifi_list()
                        
                        def wifi_select():
                            selected_network = rows[wifi_cursor][0]
                            bssid = rows[wifi_cursor][1] if len(rows[wifi_cursor]) > 1 else ""
                            logging.info("Wybrana siec: %s (%s)", selected_network, bssid)
                            
                            image = Image.new('1', (epd.height, epd.width), 255)
                            draw = ImageDraw.Draw(image)
                            draw.text((10, 10), "Deauth: " + selected_network[:15], font=font_item, fill=0)
                            epd.displayPartial(epd.getbuffer(image))
                            
                            if bssid:
                                deauth(bssid, "wlan0mon")
                            
                            time.sleep(2)
                            return_to_menu()
                        
                        btn_up.when_pressed = wifi_up
                        btn_down.when_pressed = wifi_down
                        btn_select.when_pressed = wifi_select
                        draw_wifi_list()
                    
                    def deauth_all_networks():
                        image = Image.new('1', (epd.height, epd.width), 255)
                        draw = ImageDraw.Draw(image)
                        draw.text((10, 10), "Deauth All...", font=font_item, fill=0)
                        epd.displayPartial(epd.getbuffer(image))
                        
                        for row in rows:
                            bssid = row[1] if len(row) > 1 else ""
                            if bssid:
                                logging.info("Deauth all: %s", bssid)
                                deauth(bssid, "wlan0mon")
                        
                        time.sleep(2)
                        return_to_menu()
                    
                    def return_to_menu():
                        btn_up.when_pressed = old_up
                        btn_down.when_pressed = old_down
                        btn_select.when_pressed = old_select
                        image = draw_menu_image(current_index)
                        epd.displayPartial(epd.getbuffer(image))
                    
                    btn_up.when_pressed = deauth_menu_up
                    btn_down.when_pressed = deauth_menu_down
                    btn_select.when_pressed = deauth_menu_select
                    
                    draw_deauth_menu()
                pass
            if menu_item == "Probe Request Flood":
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Probe Request Flood...", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                logging.info("Starting Probe Request Flood...")
                
                probe_request_flood("wlan0mon")
                
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Flood zakonczony", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                time.sleep(2)
                
                image = draw_menu_image(current_index)
                epd.displayPartial(epd.getbuffer(image))
            if menu_item == "Beacon Flood":
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Beacon Flood...", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                logging.info("Starting Beacon Flood...")
                
                beacon_flood("wlan0mon")
                
                image = Image.new('1', (epd.height, epd.width), 255)
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), "Flood zakonczony", font=font_item, fill=0)
                epd.displayPartial(epd.getbuffer(image))
                time.sleep(2)
                
                image = draw_menu_image(current_index)
                epd.displayPartial(epd.getbuffer(image))
            if menu_item == "Power Off":
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
