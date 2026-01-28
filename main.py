#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import subprocess
import glob
import csv
import threading
import re

from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button

# Your pentest actions
from scripts.pentests import scan_wifi, deauth, probe_request_flood, beacon_flood

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "Font.ttc")
LIB_DIR = os.path.join(BASE_DIR, "lib")
DATA_SCANS = os.path.join(BASE_DIR, "data", "scans")

if os.path.exists(LIB_DIR):
    sys.path.append(LIB_DIR)

from lib.waveshare_epd import epd2in13_V4

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
font_menu = None
font_small = None

btn_up = None
btn_down = None
btn_select = None


def load_airodump_aps(csv_path):
    """Parse airodump-ng CSV and return AP list: {bssid, channel, privacy, essid}.
    Stops at 'Station MAC' section.
    """
    aps = []
    with open(csv_path, newline='', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = None
        for row in reader:
            if not row:
                continue

            first = row[0].strip().lower()
            if first == "station mac":
                break
            if first == "bssid":
                header = [c.strip().lower() for c in row]
                continue
            if not header:
                continue

            def get(col, default=""):
                if col in header:
                    i = header.index(col)
                    return row[i].strip() if i < len(row) else default
                return default

            bssid = get("bssid")
            if not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", bssid):
                continue

            aps.append({
                "bssid": bssid,
                "channel": get("channel"),
                "privacy": get("privacy"),
                "essid": get("essid"),
            })

    return aps


# Display update helpers

def display_full(image):
    epd.display(epd.getbuffer(image))


def display_partial(image):
    epd.displayPartial(epd.getbuffer(image))


def draw_menu_image(index):
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    draw.text((10, 5), "Menu", font=font_menu, fill=0)

    y = 35
    for i, item in enumerate(menu_items):
        prefix = "> " if i == index else "  "
        draw.text((10, y), prefix + item, font=font_small, fill=0)
        y += 18

    return image


def draw_text_screen(lines, full=True):
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    y = 5
    for line in lines:
        draw.text((10, y), line, font=font_small, fill=0)
        y += 14

    if full:
        display_full(image)
    else:
        display_partial(image)


def clear_screen():
    epd.init()
    epd.Clear(0xFF)
    epd.sleep()


def power_off():
    draw_text_screen(["Power off..."], full=True)
    time.sleep(1)
    clear_screen()
    subprocess.run(['sudo', 'poweroff'])


def render_menu(full=False):
    image = draw_menu_image(current_index)
    if full:
        display_full(image)
    else:
        display_partial(image)


def scan_wifi_view():
    draw_text_screen(["Scanning WiFi...", "wait 30s"], full=True)

    # Note: scan_wifi must write to data/scans/*.csv
    scan_wifi("wlan0mon")

    os.makedirs(DATA_SCANS, exist_ok=True)
    csv_files = glob.glob(os.path.join(DATA_SCANS, "*.csv"))
    if not csv_files:
        draw_text_screen(["No CSV in", "data/scans"], full=True)
        time.sleep(2)
        render_menu(full=True)
        return

    latest_csv = max(csv_files, key=os.path.getmtime)
    aps = load_airodump_aps(latest_csv)
    if not aps:
        draw_text_screen(["No AP in CSV"], full=True)
        time.sleep(2)
        render_menu(full=True)
        return

    old_up, old_down, old_select = btn_up.when_pressed, btn_down.when_pressed, btn_select.when_pressed

    state = {"cursor": 0, "start": 0}
    PER_PAGE = 5

    def draw(full=False):
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        draw.text((10, 5), "AP list", font=font_small, fill=0)

        start = state["start"]
        end = min(start + PER_PAGE, len(aps))
        y = 25

        for idx in range(start, end):
            ap = aps[idx]
            prefix = "> " if idx == state["cursor"] else "  "
            essid = (ap["essid"] or "<hidden>")[:14]
            ch = ap["channel"] or "?"
            priv = (ap["privacy"] or "?")[:6]
            line = f"{essid} ch{ch} {priv}"
            draw.text((10, y), prefix + line, font=font_small, fill=0)
            y += 18

        draw.text((10, epd.width - 16), "SELECT: back", font=font_small, fill=0)

        if full:
            display_full(image)
        else:
            display_partial(image)

    def up():
        if state["cursor"] > 0:
            state["cursor"] -= 1
        if state["cursor"] < state["start"]:
            state["start"] = state["cursor"]
        draw(full=False)

    def down():
        if state["cursor"] < len(aps) - 1:
            state["cursor"] += 1
        if state["cursor"] >= state["start"] + PER_PAGE:
            state["start"] = state["cursor"] - PER_PAGE + 1
        draw(full=False)

    def back_to_menu():
        btn_up.when_pressed, btn_down.when_pressed, btn_select.when_pressed = old_up, old_down, old_select
        render_menu(full=True)

    btn_up.when_pressed = up
    btn_down.when_pressed = down
    btn_select.when_pressed = back_to_menu

    # full refresh on entering new screen
    draw(full=True)


def deauth_view():
    os.makedirs(DATA_SCANS, exist_ok=True)
    csv_files = glob.glob(os.path.join(DATA_SCANS, "*.csv"))
    if not csv_files:
        draw_text_screen(["No scans in", "data/scans"], full=True)
        time.sleep(2)
        render_menu(full=True)
        return

    latest_csv = max(csv_files, key=os.path.getmtime)
    aps = load_airodump_aps(latest_csv)
    if not aps:
        draw_text_screen(["No AP in CSV"], full=True)
        time.sleep(2)
        render_menu(full=True)
        return

    old_up, old_down, old_select = btn_up.when_pressed, btn_down.when_pressed, btn_select.when_pressed

    state = {"screen": "mode", "cursor": 0, "start": 0}
    proc = {"p": None}
    output = []

    def restore_menu():
        btn_up.when_pressed, btn_down.when_pressed, btn_select.when_pressed = old_up, old_down, old_select
        render_menu(full=True)

    def draw_mode(full=False):
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        draw.text((10, 5), "Deauth:", font=font_small, fill=0)
        opts = ["Single AP", "Deauth All", "Back"]
        y = 25
        for i, txt in enumerate(opts):
            prefix = "> " if i == state["cursor"] else "  "
            draw.text((10, y), prefix + txt, font=font_small, fill=0)
            y += 18

        if full:
            display_full(image)
        else:
            display_partial(image)

    def draw_ap_list(full=False):
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        draw.text((10, 5), "Pick AP:", font=font_small, fill=0)

        PER_PAGE = 5
        start = state["start"]
        end = min(start + PER_PAGE, len(aps))
        y = 25

        for idx in range(start, end):
            ap = aps[idx]
            prefix = "> " if idx == state["cursor"] else "  "
            essid = (ap["essid"] or "<hidden>")[:14]
            ch = ap["channel"] or "?"
            priv = (ap["privacy"] or "?")[:6]
            draw.text((10, y), prefix + f"{essid} ch{ch} {priv}", font=font_small, fill=0)
            y += 18

        draw.text((10, epd.width - 16), "SEL: start", font=font_small, fill=0)

        if full:
            display_full(image)
        else:
            display_partial(image)

    def draw_output(full=False):
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        draw.text((10, 5), "Deauth running", font=font_small, fill=0)
        y = 20
        for line in output[-6:]:
            draw.text((10, y), line[:40], font=font_small, fill=0)
            y += 12
        draw.text((10, epd.width - 16), "SELECT: stop", font=font_small, fill=0)

        if full:
            display_full(image)
        else:
            display_partial(image)

    def stop_deauth():
        p = proc["p"]
        proc["p"] = None
        if p:
            p.terminate()
            try:
                p.wait(timeout=2)
            except Exception:
                pass
        restore_menu()

    def start_deauth(cmd):
        output.clear()
        proc["p"] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        def reader():
            for line in proc["p"].stdout:
                output.append(line.strip())
        threading.Thread(target=reader, daemon=True).start()

        state["screen"] = "output"
        btn_up.when_pressed = None
        btn_down.when_pressed = None
        btn_select.when_pressed = stop_deauth

        # Full refresh on screen switch
        draw_output(full=True)

        # Periodic refresh so it doesn't look frozen
        def refresher():
            while state["screen"] == "output" and proc["p"] is not None:
                draw_output(full=False)
                time.sleep(0.25)

        threading.Thread(target=refresher, daemon=True).start()

    def up():
        if state["screen"] == "mode":
            state["cursor"] = (state["cursor"] - 1) % 3
            draw_mode(full=False)
        elif state["screen"] == "list":
            if state["cursor"] > 0:
                state["cursor"] -= 1
            if state["cursor"] < state["start"]:
                state["start"] = state["cursor"]
            draw_ap_list(full=False)

    def down():
        if state["screen"] == "mode":
            state["cursor"] = (state["cursor"] + 1) % 3
            draw_mode(full=False)
        elif state["screen"] == "list":
            if state["cursor"] < len(aps) - 1:
                state["cursor"] += 1
            PER_PAGE = 5
            if state["cursor"] >= state["start"] + PER_PAGE:
                state["start"] = state["cursor"] - PER_PAGE + 1
            draw_ap_list(full=False)

    def select():
        if state["screen"] == "mode":
            if state["cursor"] == 0:
                state["screen"] = "list"
                state["cursor"] = 0
                state["start"] = 0
                draw_ap_list(full=True)
            elif state["cursor"] == 1:
                start_deauth(["mdk4", "wlan0mon", "d"])
            else:
                restore_menu()

        elif state["screen"] == "list":
            ap = aps[state["cursor"]]
            start_deauth(["mdk4", "wlan0mon", "d", "-b", ap["bssid"]])

    btn_up.when_pressed = up
    btn_down.when_pressed = down
    btn_select.when_pressed = select

    # Full refresh on entering mode menu
    draw_mode(full=True)


def main():
    global epd, font_menu, font_small, current_index, btn_up, btn_down, btn_select

    epd = epd2in13_V4.EPD()
    epd.init()

    font_menu = ImageFont.truetype(FONT_PATH, 16)
    font_small = ImageFont.truetype(FONT_PATH, 10)

    os.makedirs(DATA_SCANS, exist_ok=True)

    btn_select = Button(BTN_SELECT_PIN, pull_up=True, bounce_time=0.2)
    btn_up     = Button(BTN_UP_PIN,     pull_up=True, bounce_time=0.2)
    btn_down   = Button(BTN_DOWN_PIN,   pull_up=True, bounce_time=0.2)

    def on_up():
        global current_index
        current_index = (current_index - 1) % len(menu_items)
        render_menu(full=False)

    def on_down():
        global current_index
        current_index = (current_index + 1) % len(menu_items)
        render_menu(full=False)

    def on_select():
        item = menu_items[current_index]
        logging.info("Selected: %s", item)

        if item == "Scan WiFi":
            scan_wifi_view()
            return

        if item == "Deauth":
            deauth_view()
            return

        if item == "Probe Request Flood":
            draw_text_screen(["Probe flood..."], full=True)
            probe_request_flood("", "wlan0mon")
            draw_text_screen(["Done"], full=True)
            time.sleep(1)
            render_menu(full=True)
            return

        if item == "Beacon Flood":
            draw_text_screen(["Beacon flood..."], full=True)
            beacon_flood("", "wlan0mon")
            draw_text_screen(["Done"], full=True)
            time.sleep(1)
            render_menu(full=True)
            return

        if item == "Power Off":
            power_off()
            return

    btn_up.when_pressed = on_up
    btn_down.when_pressed = on_down
    btn_select.when_pressed = on_select

    # Full refresh on first menu
    render_menu(full=True)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        clear_screen()
        epd2in13_V4.epdconfig.module_exit(cleanup=True)


if __name__ == "__main__":
    main()
