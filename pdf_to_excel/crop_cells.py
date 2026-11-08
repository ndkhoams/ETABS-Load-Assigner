"""Cat cac o can kiem tra bang mat tu strip (200 dpi) thanh 1 anh
contact sheet de doi chieu voi gia tri OCR. Dung cho cac flag
bad-parse / blank / low-conf tren gia tri khac 0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_convert import BANDS, detect_grid

from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent
JSON = WORK / "ocr_results.json"
STRIPS = Path("/tmp/bangnl/strips")

# (band, ten dong, diem, thanh phan)
WATCH = [
    ("SH4-T1", "Wind +Y", "22 / E", "Vz"),
    ("SH4-T1", "Wind -Y", "21 / E", "Hy"),
    ("SH4-T4", "Wind -Y", "43 / D", "Vz"),
    ("SH5-T3", "Wind -Y", "70 / E", "Hy"),
    ("SH5-T4", "Wind -Y", "79 / E", "Hy"),
    ("SH6-T2", "Friction +X", "89.1 / D.2", "Hx"),
    ("SH6-T2", "Wind +Y", "85.1 / E.2", "Vz"),
    ("SH6-T2", "Wind -Y", "85.1 / E.2", "Vz"),
    ("SH6-T3a", "Wind +Y", "90 / D.1", "Hx"),
    ("SH6-T3a", "Wind -Y", "90 / D.1", "Hx"),
    ("SH6-T3a", "Temperatur DT = 16°C", "90 / D.1", "Hy"),
    ("SH6-T3a", "Temperatur DT = 16°C", "92 / E.1", "Vz"),
    ("SH6-T3a", "Imperfektion X", "90 / D.1", "Hy"),
    ("SH6-T3a", "Wind +X", "90 / D.1", "Hy"),
    ("SH6-T3a", "Live load belt tension BC-5A max/min", "92 / D.1", "Hy"),
    ("SH6-T3a", "Live load Lifting jack #1 (service load 16 kN)", "92 / E.1", "Vz"),
    ("SH6-T3a", "Live load Lifting jack #2 (service load 16 kN)", "92 / E.1", "Vz"),
    ("SH6-T1", "Special load overload belt BC-5A", "82 / E", "Vz"),
    ("SH6-T2", "Live load Lifting jack #1 (service load 16 kN)", "87 / E.2", "Hx"),
]


def cell_crop(band_name, row_name, point, comp):
    band = next(b for b in BANDS if b[1] == band_name)
    strip_path = STRIPS / f"{band_name}.png"
    rows, cols, _ = detect_grid(strip_path)
    data = json.loads(JSON.read_text(encoding="utf-8"))[band_name]
    r = 3 + [x["name"] for x in data["rows"]].index(row_name)
    k = data["points"].index(point)
    c = 2 + k * 3 + ("Hx", "Hy", "Vz").index(comp)
    im = Image.open(strip_path)
    x0, y0 = int(cols[c]) - 6, int(rows[r]) - 4
    x1, y1 = int(cols[c + 1]) + 6, int(rows[r + 1]) + 4
    crop = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS)
    return crop


def main():
    tiles = []
    for band, row, pt, comp in WATCH:
        try:
            tiles.append((f"{band} | {row} | {pt} {comp}", cell_crop(band, row, pt, comp)))
        except Exception as e:
            print("FAIL", band, row, pt, comp, e)
    cols = 3
    tw = max(t.width for _, t in tiles)
    th = max(t.height for _, t in tiles)
    sheet = Image.new("RGB", (cols * (tw + 10) + 10, ((len(tiles) + cols - 1) // cols) * (th + 34) + 10), "white")
    d = ImageDraw.Draw(sheet)
    for i, (label, t) in enumerate(tiles):
        x = 10 + (i % cols) * (tw + 10)
        y = 10 + (i // cols) * (th + 34)
        d.text((x, y), label, fill="black")
        sheet.paste(t, (x, y + 22))
    out = Path("/tmp/bangnl/watch_cells.png")
    sheet.save(out)
    print(f"wrote {out} {sheet.size} tiles={len(tiles)}")


if __name__ == "__main__":
    main()
