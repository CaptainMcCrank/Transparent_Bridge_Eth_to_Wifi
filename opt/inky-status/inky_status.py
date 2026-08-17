#!/usr/bin/env python3
"""Status display for an Inky e-paper panel.

Renders three bands of information -- host/IP, Wi-Fi (client or AP), uptime --
and rotates their order once a day so no single element sits in the same place
long enough to ghost the e-ink panel.

The rotation is derived from the date rather than stored state, so the layout
is the same no matter how often this runs or whether the Pi was rebooted.

On this project's bridge device the wlan interface is a hostapd access point,
not a client, so the Wi-Fi band shows the AP's SSID and associated station
count. On a device associated as a client it shows SSID and signal instead.

Usage:
    inky_status.py                  render to the attached Inky panel
    inky_status.py --out prev.png   render to a PNG instead (no hardware)
    inky_status.py --simulate       use canned client-mode data (for previews)
    inky_status.py --simulate-ap    use canned AP-mode data (for previews)
    inky_status.py --day N          force the rotation day (for previewing)
"""

import argparse
import datetime
import itertools
import json
import os
import re
import shutil
import socket
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

WHITE, BLACK, ACCENT = 0, 1, 2

# Inky panels are black/white plus one accent ink -- red on most, yellow on
# some. The palette below is only used for PNG previews; the panel supplies
# its own.
PALETTE = [255, 255, 255, 0, 0, 0, 200, 40, 40] + [0, 0, 0] * 253

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
]


# --------------------------------------------------------------------------
# data collection
# --------------------------------------------------------------------------


# iw and ip live in /usr/sbin, which is absent from the PATH of a non-login
# shell and not guaranteed in a unit's PATH either. Resolve against an explicit
# list so the lookup does not depend on how we were invoked.
SEARCH_PATH = os.pathsep.join([
    "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin",
])


def run(cmd, timeout=5):
    """Run a command, returning stdout or '' on any failure."""
    exe = shutil.which(cmd[0], path=SEARCH_PATH)
    if not exe:
        return ""
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True,
                             text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def primary_interface():
    """Interface carrying the default route, or None."""
    out = run(["ip", "-j", "route", "show", "default"])
    if out:
        try:
            routes = json.loads(out)
        except json.JSONDecodeError:
            routes = []
        for r in routes:
            if r.get("dev"):
                return r["dev"]
    # Fall back to the first non-loopback interface that is up with an address.
    out = run(["ip", "-j", "-4", "addr", "show", "scope", "global", "up"])
    try:
        for link in json.loads(out or "[]"):
            if link.get("addr_info"):
                return link.get("ifname")
    except json.JSONDecodeError:
        pass
    return None


def ipv4_for(iface):
    """First global IPv4 address on iface, or None."""
    if not iface:
        return None
    out = run(["ip", "-j", "-4", "addr", "show", "dev", iface, "scope", "global"])
    try:
        for link in json.loads(out or "[]"):
            for addr in link.get("addr_info", []):
                if addr.get("family") == "inet" and addr.get("local"):
                    return addr["local"]
    except json.JSONDecodeError:
        pass
    return None


def dbm_to_percent(dbm):
    """Rough signal quality percentage from RSSI, matching nmcli's scale."""
    return max(0, min(100, int(2 * (dbm + 100))))


def ap_status():
    """(iface, ssid, station_count) for a local AP interface, else Nones.

    A hostapd bridge has no NetworkManager and its wlan is never "associated",
    so the client-mode probes below would report "no wi-fi" forever. `iw dev`
    labels an AP interface with `type AP` and carries its SSID.
    """
    iface = ssid = None
    current = {"name": None, "ssid": None}
    for line in run(["iw", "dev"]).splitlines():
        s = line.strip()
        if s.startswith("Interface "):
            current = {"name": s.split(None, 1)[1], "ssid": None}
        elif s.startswith("ssid "):
            current["ssid"] = s.split(None, 1)[1]
        elif s == "type AP" and current["name"]:
            iface, ssid = current["name"], current["ssid"]
            break
    if not iface:
        return None, None, None
    dump = run(["iw", "dev", iface, "station", "dump"])
    stations = sum(1 for line in dump.splitlines() if line.startswith("Station "))
    return iface, ssid, stations


def wifi_status(iface):
    """(ssid, percent, dbm) for the associated network; ssid None if not on Wi-Fi."""
    ssid = percent = dbm = None

    # `iw` reports the SSID and RSSI of the link we are actually associated
    # with, which is what we want -- nmcli's scan list can hold stale entries.
    if iface:
        out = run(["iw", "dev", iface, "link"])
        if out and "Not connected" not in out:
            m = re.search(r"^\s*SSID:\s*(.+?)\s*$", out, re.M)
            if m:
                ssid = m.group(1)
            m = re.search(r"signal:\s*(-?\d+)\s*dBm", out)
            if m:
                dbm = int(m.group(1))

    # NetworkManager knows the percentage it is using for its own UI; prefer
    # it when present so the display agrees with `nmcli dev wifi`.
    out = run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"])
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[0] == "yes":
            ssid = ssid or parts[1] or None
            if parts[2].isdigit():
                percent = int(parts[2])
            break

    # Last resort: the kernel's own link-quality counter.
    if ssid and percent is None and dbm is None:
        try:
            with open("/proc/net/wireless") as fh:
                for line in fh:
                    if iface and line.strip().startswith(iface + ":"):
                        fields = line.split()
                        dbm = int(float(fields[3]))
                        break
        except (OSError, ValueError, IndexError):
            pass

    if percent is None and dbm is not None:
        percent = dbm_to_percent(dbm)
    return ssid, percent, dbm


def uptime_seconds():
    try:
        with open("/proc/uptime") as fh:
            return float(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def format_uptime(seconds):
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def collect(simulate=False, simulate_ap=False):
    if simulate or simulate_ap:
        data = {
            "hostname": "WifiAP" if simulate_ap else "ansibledest",
            "iface": "br0" if simulate_ap else "wlan0",
            "ip": "192.168.110.195",
            "ssid": None if simulate_ap else "workshop",
            "percent": None if simulate_ap else 72,
            "dbm": None if simulate_ap else -64,
            "uptime": 5 * 86400 + 3 * 3600,
            "ap_iface": "wlan0" if simulate_ap else None,
            "ap_ssid": "workshop" if simulate_ap else None,
            "stations": 3 if simulate_ap else None,
        }
        return data
    iface = primary_interface()
    ap_iface, ap_ssid, stations = ap_status()
    if ap_ssid:
        ssid = percent = dbm = None
    else:
        ssid, percent, dbm = wifi_status(iface)
    return {
        "hostname": socket.gethostname(),
        "iface": iface,
        "ip": ipv4_for(iface),
        "ssid": ssid,
        "percent": percent,
        "dbm": dbm,
        "uptime": uptime_seconds(),
        "ap_iface": ap_iface,
        "ap_ssid": ap_ssid,
        "stations": stations,
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def load_fonts(big, small, tiny):
    for bold_path, regular_path in FONT_CANDIDATES:
        if os.path.exists(bold_path) and os.path.exists(regular_path):
            return (ImageFont.truetype(bold_path, big),
                    ImageFont.truetype(regular_path, small),
                    ImageFont.truetype(bold_path, tiny))
    default = ImageFont.load_default()
    return default, default, default


def text_height(draw, font):
    return draw.textbbox((0, 0), "Ag", font=font)[3]


def band_text_top(draw, y, h, fonts):
    """Y for the first of a band's two text lines, centred in the band.

    Centring rather than top-aligning keeps descenders clear of the rule drawn
    at the band boundary.
    """
    big, small, _ = fonts
    content = text_height(draw, big) + 1 + text_height(draw, small)
    return y + max(0, (h - 3 - content) // 2)


def ellipsize(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def draw_bars(draw, x, y, height, percent, colour):
    """Five-step signal meter; unfilled steps stay as outlines."""
    count, width, gap = 5, 4, 2
    filled = 0 if percent is None else max(1, round(percent / 100 * count))
    for i in range(count):
        bar_h = int(height * (0.35 + 0.65 * (i + 1) / count))
        bx = x + i * (width + gap)
        by = y + height - bar_h
        box = (bx, by, bx + width - 1, y + height - 1)
        if i < filled:
            draw.rectangle(box, fill=colour)
        else:
            draw.rectangle(box, outline=BLACK)
    return count * width + (count - 1) * gap


def band_host(draw, box, fonts, data, accent):
    x, y, w, h = box
    big, small, _ = fonts
    colour = ACCENT if accent else BLACK
    y = band_text_top(draw, y, h, fonts)
    name = ellipsize(draw, data["hostname"] or "unknown", big, w)
    draw.text((x, y), name, font=big, fill=colour)
    y += text_height(draw, big) + 1
    ip = data["ip"] or "no address"
    iface = data["iface"] or "?"
    draw.text((x, y), ellipsize(draw, f"{ip}  ({iface})", small, w), font=small, fill=BLACK)


def band_wifi(draw, box, fonts, data, accent):
    if data.get("ap_ssid"):
        return band_ap(draw, box, fonts, data, accent)

    x, y, w, h = box
    big, small, _ = fonts
    colour = ACCENT if accent else BLACK

    meter_w = draw_bars(draw, x + w - 28, y + 4, h - 11, data["percent"], colour)
    text_w = w - meter_w - 6

    y = band_text_top(draw, y, h, fonts)
    ssid = data["ssid"] or "no wi-fi"
    draw.text((x, y), ellipsize(draw, ssid, big, text_w), font=big, fill=colour)
    y += text_height(draw, big) + 1

    if data["percent"] is None and data["dbm"] is None:
        detail = "not associated"
    elif data["dbm"] is not None and data["percent"] is not None:
        detail = f"{data['percent']}%  {data['dbm']} dBm"
    elif data["percent"] is not None:
        detail = f"{data['percent']}%"
    else:
        detail = f"{data['dbm']} dBm"
    draw.text((x, y), ellipsize(draw, detail, small, text_w), font=small, fill=BLACK)


def band_ap(draw, box, fonts, data, accent):
    """Access-point variant of the Wi-Fi band: SSID we radiate + station count."""
    x, y, w, h = box
    big, small, _ = fonts
    colour = ACCENT if accent else BLACK
    y = band_text_top(draw, y, h, fonts)
    ssid = data["ap_ssid"] or "AP"
    draw.text((x, y), ellipsize(draw, f"AP {ssid}", big, w), font=big, fill=colour)
    y += text_height(draw, big) + 1
    n = data["stations"] or 0
    detail = f"{n} client{'' if n == 1 else 's'}  ({data['ap_iface'] or '?'})"
    draw.text((x, y), ellipsize(draw, detail, small, w), font=small, fill=BLACK)


def band_uptime(draw, box, fonts, data, accent):
    x, y, w, h = box
    big, small, _ = fonts
    colour = ACCENT if accent else BLACK
    y = band_text_top(draw, y, h, fonts)
    draw.text((x, y), f"up {format_uptime(data['uptime'])}", font=big, fill=colour)
    y += text_height(draw, big) + 1
    stamp = data["now"].strftime("%a %d %b %H:%M")
    draw.text((x, y), ellipsize(draw, stamp, small, w), font=small, fill=BLACK)


BANDS = [band_host, band_wifi, band_uptime]
ORDERS = list(itertools.permutations(range(len(BANDS))))


def render(width, height, data, day_ordinal):
    img = Image.new("P", (width, height), WHITE)
    img.putpalette(PALETTE)
    draw = ImageDraw.Draw(img)

    if width >= 250:
        fonts = load_fonts(16, 12, 9)
    else:
        fonts = load_fonts(13, 10, 8)

    margin = 4
    # Cycle the band order daily, and drift the whole block by a couple of
    # pixels on a slower cycle, so edges of glyphs never land on one spot.
    order = ORDERS[day_ordinal % len(ORDERS)]
    jitter = (day_ordinal // len(ORDERS)) % 3
    accent_band = day_ordinal % len(BANDS)

    top = margin + jitter
    usable = height - top - margin
    band_h = usable // len(BANDS)

    for slot, band_index in enumerate(order):
        y = top + slot * band_h
        box = (margin, y, width - 2 * margin, band_h)
        BANDS[band_index](draw, box, fonts, data, accent=(band_index == accent_band))
        if slot < len(order) - 1:
            rule_y = y + band_h - 2
            draw.line((margin, rule_y, width - margin, rule_y), fill=BLACK)

    return img


# --------------------------------------------------------------------------

def open_panel(board, colour):
    """Open the Inky display.

    Boards made before Pimoroni added the identifying EEPROM cannot be probed,
    so allow the type to be named explicitly instead of relying on auto().
    """
    if board == "auto":
        from inky.auto import auto
        return auto()
    if board == "phat":
        from inky import InkyPHAT
        return InkyPHAT(colour)
    if board == "phat1608":
        from inky import InkyPHAT_SSD1608
        return InkyPHAT_SSD1608(colour)
    if board == "what":
        from inky import InkyWHAT
        return InkyWHAT(colour)
    raise ValueError(f"unknown board {board!r} (use auto, phat, phat1608 or what)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write a PNG here instead of the panel")
    parser.add_argument("--simulate", action="store_true",
                        help="use canned client-mode data")
    parser.add_argument("--simulate-ap", action="store_true",
                        help="use canned access-point-mode data")
    parser.add_argument("--day", type=int, help="force rotation day ordinal")
    parser.add_argument("--size", help="WxH for --out when no panel present",
                        default="212x104")
    parser.add_argument("--board", default=os.environ.get("INKY_BOARD", "auto"),
                        choices=["auto", "phat", "phat1608", "what"],
                        help="panel type; auto needs the ID EEPROM")
    parser.add_argument("--colour", default=os.environ.get("INKY_COLOUR", "red"),
                        choices=["red", "yellow", "black"],
                        help="accent ink, for manually named boards")
    args = parser.parse_args()

    now = datetime.datetime.now()
    data = collect(simulate=args.simulate, simulate_ap=args.simulate_ap)
    data["now"] = now
    day_ordinal = args.day if args.day is not None else now.date().toordinal()

    inky = None
    if not args.out:
        try:
            inky = open_panel(args.board, args.colour)
        except Exception as exc:                       # noqa: BLE001
            print(f"could not open Inky display: {exc}", file=sys.stderr)
            return 1

    if inky is not None:
        width, height = inky.resolution
    else:
        width, height = (int(v) for v in args.size.lower().split("x"))

    img = render(width, height, data, day_ordinal)

    if args.out:
        img.convert("RGB").save(args.out)
        print(f"wrote {args.out} ({width}x{height}, day {day_ordinal})")
        return 0

    inky.set_image(img)
    inky.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
