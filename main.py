"""Entry point ETABS Load Assigner.

Chay GUI:  python main.py
Kiem tra import: python main.py --no-gui
"""
import argparse
import sys

from etabs_loader import __version__


def build_parser():
    p = argparse.ArgumentParser(
        prog="ETABS-Load-Assigner",
        description="Gan tai mong tu file Excel/PDF vao ETABS (theo pattern, phuong/chieu do user chot).")
    p.add_argument("--version", action="version", version=f"ETABS Load Assigner {__version__}")
    p.add_argument("--no-gui", action="store_true", help="Chi kiem tra import, khong mo giao dien.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.no_gui:
        print(f"ETABS Load Assigner {__version__} — import OK (khong mo GUI).")
        return 0
    try:
        from etabs_loader.app import run
    except ImportError as e:
        print(f"Khong mo duoc giao dien Tkinter: {e}", file=sys.stderr)
        return 1
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
