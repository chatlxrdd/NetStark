#!/usr/bin/env python3

import time
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
from gpiozero import Button

# GPIO pin assignments (physical pins: 11 -> GPIO17, 13 -> GPIO27, 15 -> GPIO22)
UP_PIN = 29
DOWN_PIN = 31
SELECT_PIN = 33

# Initialize buttons with internal pull-ups
up_button = Button(UP_PIN, pull_up=True)
down_button = Button(DOWN_PIN, pull_up=True)
select_button = Button(SELECT_PIN, pull_up=True)

# Menu data
menu_items = [
    "deauth",
    "injection",
    "marruder",
]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
current_index = 0  # Which item is highlighted
serial = i2c(port=1, address=0x3C) # I2C address for the OLED display
device = ssd1306(serial, width=128, height=32)

def deauth():
   deatuh_menu_items = [
       "attack",
       "back to menu"
   ]
   while True:
        global current_index
        # Check button states
        if up_button.is_pressed:
            current_index = (current_index - 1) % len(deatuh_menu_items)
            time.sleep(0.05)  # Debounce: short delay so we don't double-trigger
        elif down_button.is_pressed:
            current_index = (current_index + 1) % len(deatuh_menu_items)
            time.sleep(0.05)
        elif select_button.is_pressed:
            # Do something when the user selects the current item
            selected_item = deatuh_menu_items[current_index]
            if selected_item == "attack":
                print('Attacking...')
            elif selected_item == "back to menu":
                main()
            print(f"Selected: {selected_item}")
            time.sleep(0.05)

        # Draw the menu on the screen
        with canvas(device) as draw:
            y_offset = 0
            for i, item in enumerate(deatuh_menu_items):
                # If it's the selected index, draw an arrow or brackets:
                if i == current_index:
                    prefix = " > "  # to highlight
                else:
                    prefix = "  "

                text = prefix + item
                draw.text((0, y_offset), text, fill=255, font=font)
                y_offset += 8
        time.sleep(0.1)

def injection():
    while True:
        with canvas(device) as draw:
            draw.text((0,0), 'Hello Alan!', font = font, fill = 255)

def marruder():
    while True:
        with canvas(device) as draw:
            draw.text((0,0), 'Hello Alan!', font = font, fill = 255)


def main():

    # Optionally, load a TTF font. For the built-in font, just use None.
    # Increase the size if you have a bigger display or want bigger text.
    

    global current_index

    with canvas(device) as draw:
        draw.text((0,0), 'Hello Alan!', font = font, fill = 255)

    time.sleep(3)

    # We'll repeatedly update the display in a loop
    while True:
        # Check button states
        if up_button.is_pressed:
            current_index = (current_index - 1) % len(menu_items)
            time.sleep(0.05)  # Debounce: short delay so we don't double-trigger
        elif down_button.is_pressed:
            current_index = (current_index + 1) % len(menu_items)
            time.sleep(0.05)
        elif select_button.is_pressed:
            # Do something when the user selects the current item
            selected_item = menu_items[current_index]
            if selected_item == "deauth":
                deauth()
            elif selected_item == "injection":
                injection()
            elif selected_item == "marruder":
                marruder()
            # For now, just print the selected item to the console
            print(f"Selected: {selected_item}")
            # We'll just sleep a bit so we don't spam output
            time.sleep(0.05)

        # Draw the menu on the screen
        with canvas(device) as draw:
            # For a 128x32 display, we don't have much vertical space, so just show them all.
            # If you want to show fewer items at a time, you'd slice the list or do some
            # "scroll window" logic. But let's keep it simple: 5 items can still fit with small text.
            y_offset = 0

            for i, item in enumerate(menu_items):
                # If it's the selected index, draw an arrow or brackets:
                if i == current_index:
                    prefix = " > "  # to highlight
                else:
                    prefix = "  "

                text = prefix + item
                draw.text((0, y_offset), text, fill=255, font=font)
                y_offset += 8  # Move down for the next line

        # Small delay to limit refresh rate
        time.sleep(0.1)

if __name__ == "__main__":
    main()

