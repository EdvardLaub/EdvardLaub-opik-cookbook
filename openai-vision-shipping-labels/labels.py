"""Fictional shipping labels, drawn with Pillow at run time.

`LABELS` holds the ground truth for eight labels: four clean ones and four
deliberately hard ones (skewed, smudged over the tracking number, a weight
struck through with a handwritten correction, and a low-resolution noisy
scan). `render_label` draws one into a PNG under labels/. Nothing here is
committed as an image: the app regenerates the PNGs whenever it runs, and the
same random seed gives the same pixels every time.

Every person, street and tracking number below is invented.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

LABEL_DIR = Path(__file__).parent / "labels"
W, H = 640, 940

# Font candidates, best first (macOS paths). Pillow's built-in font is the
# fallback so the script still runs elsewhere, just with plainer labels.
FONTS = {
    "sans": ["/System/Library/Fonts/Supplemental/Arial.ttf"],
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    "mono": ["/System/Library/Fonts/Supplemental/Courier New Bold.ttf"],
    "hand": ["/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _addr(name: str, street: str, city: str, region: str, postal: str, country: str) -> dict[str, str]:
    return {
        "name": name,
        "street": street,
        "city": city,
        "region": region,
        "postal_code": postal,
        "country": country,
    }


# Ground truth. `style` picks the layout; `defect` picks the hard-case
# treatment applied after drawing. `printed_weight` differs from `weight`
# only on the handwritten-correction label.
LABELS: list[dict[str, Any]] = [
    {
        "id": "01_ups_ground",
        "defect": None,
        "carrier": "UPS",
        "service_level": "UPS Ground",
        "tracking_number": "1Z 4A7 R20 03 8841 2096",
        "ship_date": "2026-03-12",
        "date_text": "Mar 12, 2026",
        "weight": {"value": 4.5, "unit": "lb"},
        "sender": _addr("Fennimore Candle Co.", "88 Quarry Lane", "Duluth", "MN", "55802", "US"),
        "recipient": _addr("Marguerite Oyelaran", "1402 Alder Court, Apt 6B", "Boise", "ID", "83702", "US"),
    },
    {
        "id": "02_fedex_priority",
        "defect": None,
        "carrier": "FedEx",
        "service_level": "FedEx Priority Overnight",
        "tracking_number": "7489 2210 5563",
        "ship_date": "2026-03-09",
        "date_text": "2026-03-09",
        "weight": {"value": 12.0, "unit": "lb"},
        "sender": _addr("Halvorsen Bike Parts", "4 Cobble Street", "Providence", "RI", "02903", "US"),
        "recipient": _addr("Tobias Wren", "930 Larkspur Avenue", "Santa Fe", "NM", "87501", "US"),
    },
    {
        "id": "03_usps_priority",
        "defect": None,
        "carrier": "USPS",
        "service_level": "USPS Priority Mail",
        "tracking_number": "9405 5112 0108 4567 8901 23",
        "ship_date": "2026-03-18",
        "date_text": "03/18/2026",
        "weight": {"value": 0.8, "unit": "lb"},
        "sender": _addr("Pemberton Stamps", "17 Mill Road", "Burlington", "VT", "05401", "US"),
        "recipient": _addr("Ines Castellanos", "2250 Juniper Way", "Tucson", "AZ", "85701", "US"),
    },
    {
        "id": "04_dhl_express",
        "defect": None,
        "carrier": "DHL",
        "service_level": "DHL Express Worldwide",
        "tracking_number": "48 1157 2290",
        "ship_date": "2026-03-05",
        "date_text": "05 MAR 2026",
        "weight": {"value": 2.3, "unit": "kg"},
        "sender": _addr("Kestrel Ceramics", "61 Harbour Row", "Halifax", "NS", "B3J 1S9", "CA"),
        "recipient": _addr("Lena Brandtner", "Speicherstrasse 14", "Hamburg", "", "20457", "DE"),
    },
    {
        "id": "05_ups_skewed",
        "defect": "skewed",
        "carrier": "UPS",
        "service_level": "UPS Next Day Air",
        "tracking_number": "1Z 9R3 K58 01 6275 4418",
        "ship_date": "2026-03-13",
        "date_text": "Mar 13, 2026",
        "weight": {"value": 6.0, "unit": "lb"},
        "sender": _addr("Dunmore Tea Importers", "310 Wharf Street", "Portland", "ME", "04101", "US"),
        "recipient": _addr("Anselm Okafor", "75 Birchwood Drive", "Madison", "WI", "53703", "US"),
    },
    {
        "id": "06_fedex_smudged",
        "defect": "smudged",
        "carrier": "FedEx",
        "service_level": "FedEx 2Day",
        "tracking_number": "7712 4086 9351",
        "ship_date": "2026-03-10",
        "date_text": "2026-03-10",
        "weight": {"value": 8.5, "unit": "lb"},
        "sender": _addr("Orchard & Vine Supply", "9 Fairview Road", "Asheville", "NC", "28801", "US"),
        "recipient": _addr("Priya Natarajan", "5518 Meadowlark Lane", "Spokane", "WA", "99201", "US"),
    },
    {
        "id": "07_usps_handwritten",
        "defect": "handwritten",
        "carrier": "USPS",
        "service_level": "USPS Ground Advantage",
        "tracking_number": "9400 1118 9922 3053 6417 08",
        "ship_date": "2026-03-16",
        "date_text": "03/16/2026",
        "weight": {"value": 3.5, "unit": "lb"},  # handwritten correction wins
        "printed_weight": {"value": 2.0, "unit": "lb"},  # struck through
        "sender": _addr("Lowell Vinyl Exchange", "260 Canal Street", "Lowell", "MA", "01852", "US"),
        "recipient": _addr("Dario Fontaine", "88 Ridgeview Terrace", "Omaha", "NE", "68102", "US"),
    },
    {
        "id": "08_dhl_lowres",
        "defect": "lowres",
        "carrier": "DHL",
        "service_level": "DHL Express 12:00",
        "tracking_number": "73 9042 1186",
        "ship_date": "2026-03-11",
        "date_text": "11 MAR 2026",
        "weight": {"value": 18.7, "unit": "kg"},
        "sender": _addr("Nordlicht Optics", "Kaiserstrasse 8", "Leipzig", "", "04109", "DE"),
        "recipient": _addr("Claire Moreau", "17 Rue des Tanneurs", "Lyon", "", "69002", "FR"),
    },
]

BANDS = {  # header colour per carrier
    "UPS": (62, 40, 28),
    "FedEx": (77, 20, 140),
    "USPS": (30, 60, 130),
    "DHL": (200, 40, 30),
}


def _barcode(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], rng: random.Random) -> None:
    """Decorative bars; the label's real data is the human-readable text below."""
    x0, y0, x1, y1 = box
    x = x0
    while x < x1:
        w = rng.choice([2, 3, 4, 6])
        if rng.random() < 0.55:
            draw.rectangle([x, y0, min(x + w, x1), y1], fill=(10, 10, 10))
        x += w + rng.choice([2, 3, 4])


def _address_block(draw, x, y, addr, fnt, line=None) -> int:
    line = line or fnt.size + 6
    lines = [addr["name"], addr["street"]]
    region = f" {addr['region']}" if addr["region"] else ""
    lines.append(f"{addr['city']}{region} {addr['postal_code']}")
    lines.append(addr["country"])
    for text in lines:
        draw.text((x, y), text, font=fnt, fill=(15, 15, 15))
        y += line
    return y


def draw_label(spec: dict[str, Any], seed: int = 7) -> tuple[Image.Image, dict[str, tuple[int, int, int, int]]]:
    """Draw the clean label and return it with the boxes of the fields that
    hard-case treatments need to find (tracking text, weight text)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), (250, 250, 246))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W - 7, H - 7], outline=(20, 20, 20), width=4)

    # Carrier header band with the service level
    d.rectangle([10, 10, W - 11, 110], fill=BANDS[spec["carrier"]])
    d.text((30, 22), spec["carrier"].upper(), font=font("bold", 54), fill=(255, 255, 255))
    d.text((30, 80), spec["service_level"], font=font("bold", 22), fill=(255, 255, 255))

    # Sender (small, top left) and ship date / weight (top right)
    d.text((26, 124), "FROM", font=font("bold", 16), fill=(90, 90, 90))
    _address_block(d, 26, 146, spec["sender"], font("sans", 22))
    d.text((400, 124), "SHIP DATE", font=font("bold", 16), fill=(90, 90, 90))
    d.text((400, 146), spec["date_text"], font=font("bold", 24), fill=(15, 15, 15))
    d.text((400, 190), "WEIGHT", font=font("bold", 16), fill=(90, 90, 90))
    shown = spec.get("printed_weight", spec["weight"])
    weight_text = f"{shown['value']:.1f} {shown['unit'].upper()}"
    wf = font("bold", 34)
    d.text((400, 212), weight_text, font=wf, fill=(15, 15, 15))
    weight_box = (400, 212, 400 + int(d.textlength(weight_text, font=wf)), 252)

    d.line([20, 330, W - 20, 330], fill=(20, 20, 20), width=3)

    # Recipient (big)
    d.text((26, 346), "SHIP TO", font=font("bold", 18), fill=(90, 90, 90))
    _address_block(d, 26, 376, spec["recipient"], font("bold", 34), line=46)
    d.line([20, 604, W - 20, 604], fill=(20, 20, 20), width=3)

    # Barcode and the tracking number printed beneath it
    _barcode(d, (40, 630, W - 40, 790), rng)
    tf = font("mono", 34)
    track = spec["tracking_number"]
    tw = d.textlength(track, font=tf)
    tx, ty = (W - tw) / 2, 812
    d.text((tx, ty), track, font=tf, fill=(10, 10, 10))
    track_box = (int(tx), ty, int(tx + tw), ty + 40)
    d.text((26, 880), f"TRACKING #  {spec['carrier']} / {spec['id'][:2]}", font=font("sans", 14), fill=(120, 120, 120))
    return img, {"tracking": track_box, "weight": weight_box}


def _skew(img: Image.Image) -> Image.Image:
    """Rotate about 13 degrees and shear, on a darker desk background."""
    desk = Image.new("RGB", (img.width + 260, img.height + 260), (92, 84, 74))
    rotated = img.rotate(13, expand=True, resample=Image.BICUBIC, fillcolor=(92, 84, 74))
    desk.paste(rotated, (30, 30))
    return desk.transform(desk.size, Image.AFFINE, (1, 0.16, 0, 0, 1, 0), resample=Image.BICUBIC, fillcolor=(92, 84, 74))


def _smudge(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Blur and smear the right two thirds of the tracking number so that
    several digits are genuinely ambiguous."""
    x0, y0, x1, y1 = box
    sx = x0 + (x1 - x0) // 3
    region = img.crop((sx, y0 - 6, x1 + 6, y1 + 6)).filter(ImageFilter.GaussianBlur(5.5))
    img.paste(region, (sx, y0 - 6))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(5):  # grey thumb-streaks
        cx = sx + 30 + i * 38
        od.ellipse([cx, y0 - 2, cx + 70, y1 + 4], fill=(70, 70, 70, 70))
    overlay = overlay.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _handwritten(img: Image.Image, box: tuple[int, int, int, int], spec: dict[str, Any]) -> Image.Image:
    """Strike through the printed weight and write the corrected one beside it."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.line([x0 - 4, y0 + 22, x1 + 4, y0 + 14], fill=(160, 20, 20), width=4)
    new = spec["weight"]
    text = f"{new['value']:g} {new['unit']}"
    layer = Image.new("RGBA", (260, 90), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((6, 6), text, font=font("hand", 54), fill=(25, 45, 170, 255))
    layer = layer.rotate(7, expand=True, resample=Image.BICUBIC)
    base = img.convert("RGBA")
    base.alpha_composite(layer, (x0 - 6, y1 + 6))
    return base.convert("RGB")


def _lowres(img: Image.Image, seed: int) -> Image.Image:
    """Shrink, add sensor noise, rotate a little, compress: a bad phone scan."""
    rng = random.Random(seed)
    small = img.resize((W // 3, H // 3), Image.BILINEAR)
    noise = Image.effect_noise(small.size, 38).convert("RGB")
    small = ImageChops.blend(small, noise, 0.22)
    small = small.rotate(5, expand=True, resample=Image.BILINEAR, fillcolor=(120, 118, 112))
    small = small.filter(ImageFilter.GaussianBlur(0.9 + rng.random() * 0.2))
    return small.resize((small.width * 2, small.height * 2), Image.BILINEAR)


def render_label(spec: dict[str, Any], out_dir: Path = LABEL_DIR) -> Path:
    """Draw one label (plus its defect, if any) and save it as a PNG."""
    img, boxes = draw_label(spec)
    defect = spec["defect"]
    if defect == "skewed":
        img = _skew(img)
    elif defect == "smudged":
        img = _smudge(img, boxes["tracking"])
    elif defect == "handwritten":
        img = _handwritten(img, boxes["weight"], spec)
    elif defect == "lowres":
        img = _lowres(img, seed=11)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{spec['id']}.png"
    img.save(path)
    return path


def render_all(out_dir: Path = LABEL_DIR) -> dict[str, Path]:
    """Regenerate every label PNG; returns {label id: path}."""
    return {spec["id"]: render_label(spec, out_dir) for spec in LABELS}


if __name__ == "__main__":
    for label_id, path in render_all().items():
        print(f"{label_id} -> {path}")
