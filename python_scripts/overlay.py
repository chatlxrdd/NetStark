#!/usr/bin/env python3

import time
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
from gpiozero import Button

# GPIO pin assignments (physical pins: 11 -> GPIO17, 13 -> GPIO27, 15 -> GPIO22)
UP_PIN = 27
DOWN_PIN = 17
SELECT_PIN = 22

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
current_index = 0  # Which item is highlighted



def main():
    # Set up I2C interface for the display
    serial = i2c(port=1, address=0x3C)
    # Adjust width=128, height=64 if your display is 128×64
    device = ssd1306(serial, width=128, height=32)

    # Optionally, load a TTF font. For the built-in font, just use None.
    # Increase the size if you have a bigger display or want bigger text.
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    #font = None

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
                    prefix = "*"  # to highlight
                else:
                    prefix = "  "

                text = prefix + item
                draw.text((0, y_offset), text, fill=255, font=font)
                y_offset += 8  # Move down for the next line

        # Small delay to limit refresh rate
        time.sleep(0.1)

if __name__ == "__main__":
    main()

