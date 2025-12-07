import json
import re

from .key import Key
from .keyboard import Keyboard


def select(obj: dict, keys: list) -> dict:
    """Return a copy of the given dict with only the listed keys"""
    return {k: obj[k] for k in keys if k in obj}


def _parse_led_settings(notes: str, keyboard: Keyboard) -> None:
    """
    Parse LED-related settings from the KLE 'notes' string and
    store them on the Keyboard object.

    Expected format inside notes (anywhere, any line):

        led_color: #RRGGBB
        led_brightness: 1

    Parsing is case-insensitive and tolerates extra spaces.
    """
    if not notes:
        return

    # Case-insensitive search for "led_color: #RRGGBB"
    color_match = re.search(
        r"led_color\s*:\s*#([0-9a-fA-F]{6})",
        notes,
        flags=re.IGNORECASE,
    )
    if color_match is not None:
        keyboard.led_color = "#" + color_match.group(1)

    # Case-insensitive search for "led_brightness: 0.xx or 1"
    brightness_match = re.search(
        r"led_brightness\s*:\s*(1(?:\.0+)?|0(?:\.[0-9]+)?)",
        notes,
        flags=re.IGNORECASE,
    )
    if brightness_match is not None:
        try:
            keyboard.led_brightness = float(brightness_match.group(1))
        except ValueError:
            # If something weird sneaks in, just ignore it instead of crashing
            pass

    # Optional: keep the full notes string if you want later
    # keyboard.notes = notes


def load(file_path: str) -> Keyboard:
    """Parses KLE Raw JSON into a Keyboard object"""
    # load JSON file
    with open(file_path, encoding="UTF-8", errors="replace") as f:
        layout = json.load(f)

    # make empty keyboard
    keyboard = Keyboard()
    row_data = {}
    y = 0

    # iterate over rows
    for row_num, row in enumerate(layout):
        x = 0

        # check if item is a row or if it is a dict of keyboard properties
        if not isinstance(row, dict):
            # iterate over keys in row
            for pos, value in enumerate(row):
                # we skip over items that aren't keys (which are strings)
                if isinstance(value, str):
                    # default props values
                    props = {
                        "p": "",
                        "d": False,
                        "w": 1,
                        "h": 1,
                        "r": None,
                        "rx": 0,
                        "ry": 0,
                        "y": 0,
                        "c": "#cccccc",   # default key colour
                        "t": "#111111",   # default text colour
                        "f": 3,
                        "fa": None,
                        "a": 4,
                        # override defaults with any current row data
                        **row_data,
                    }

                    # if the previous item is a dict add it to props and row_data
                    prev = row[pos - 1]
                    if isinstance(prev, dict):
                        props = {**props, **prev}

                        # carry over some properties row-to-row
                        row_data = {
                            **row_data,
                            **select(prev, ["c", "t", "g", "a", "f", "f2", "p", "r", "rx"]),
                        }

                        # handle x/y offsets and rotation origins per KLE format
                        if "x" in prev:
                            x += prev["x"]

                        if "y" in prev:
                            row_data["yCoord"] = prev["y"]
                            y += prev["y"]

                        if "ry" in prev:
                            row_data["ry"] = prev["ry"]
                            if "y" in prev:
                                y = prev["ry"] + row_data["yCoord"]
                            else:
                                y = prev["ry"]
                        elif ("r" in prev and "yCoord" not in row_data) or "rx" in prev:
                            if "ry" in row_data:
                                y = row_data["ry"]
                            else:
                                row_data["ry"] = 0
                                y = 0
                            if "y" in prev:
                                y += prev["y"]

                    # merge final row_data into props once more
                    props = {**props, **row_data}

                    # create key and add to keyboard
                    key = Key(value, x, y, row_num, pos, props)
                    keyboard.add_key(key)

                    # advance x by key width
                    x += key.width

            # go to next row in KLE
            y += 1

        else:
            # if the current item is a dict then add its properties to the keyboard
            if "backcolor" in row:
                keyboard.color = row["backcolor"]
            if "name" in row:
                keyboard.name = row["name"]
            if "switchType" in row:
                keyboard.switch_type = row["switchType"]
            if "notes" in row:
                _parse_led_settings(row["notes"], keyboard)
            if "css" in row:
                keyboard.css = row["css"]

    return keyboard
