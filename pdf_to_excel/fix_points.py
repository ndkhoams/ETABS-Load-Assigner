"""Sua ten diem bi OCR ghep trung trong ocr_results.json.

Nguyen nhan: OCR doc trung 1 ten diem thanh 1 doan duy nhat
(vd '2121 / E', '881 / E') nen bo trung lap theo manh khong tach
duoc. Cac gia tri sua duoi day suy tu thu tu diem lien ke trong
cung bang + anh strip goc — moi muc deu xac dinh duy nhat.
"""
import json
from pathlib import Path

JSON = Path(__file__).resolve().parent / "ocr_results.json"

FIXES = {
    "SH4-T1": {"2121 / E": "21 / E"},
    "SH4-T3": {"34 / 34 / E": "34 / E"},
    "SH5-T1": {"48 / D48 / D": "48 / D"},
    "SH5-T2": {"52 / E52 / E": "52 / E", "55 / D55 / D": "55 / D"},
    "SH6-T1": {"881 / E": "81 / E", "83 / E83 / E": "83 / E"},
    "SH6-T2": {"8686 / D.2": "86 / D.2", "88 / D.28 / D.2": "88 / D.2"},
    "SH6-S781": {"79.2 / 79.2 / S.15": "79.2 / S.15"},
    "SH6-S801": {"81.1 / 81.1 / S.15": "81.1 / S.15"},
    "SH6-S821": {"83.1 / 83.1 / S.15": "83.1 / S.15"},
}


def main():
    data = json.loads(JSON.read_text(encoding="utf-8"))
    n = 0
    for band, mapping in FIXES.items():
        t = data.get(band)
        if not t:
            print(f"{band}: khong co trong JSON")
            continue
        for bad, good in mapping.items():
            if bad not in t["points"]:
                print(f"{band}: khong thay {bad!r} (da sua roi?)")
                continue
            t["points"] = [good if p == bad else p for p in t["points"]]
            for row in t["rows"]:
                if bad in row["values"]:
                    row["values"][good] = row["values"].pop(bad)
            t.setdefault("flags", []).append(
                {"cell": f"header {bad}", "issue": f"ten diem OCR {bad!r} -> sua tay {good!r} theo thu tu diem + anh strip"})
            n += 1
            print(f"{band}: {bad!r} -> {good!r}")
    JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"fixed {n} ten diem")


if __name__ == "__main__":
    main()
