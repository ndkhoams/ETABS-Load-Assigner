"""Build .exe Windows (PyInstaller, onefile). Chay tren Windows:
    pip install -r requirements.txt pyinstaller
    python build_exe.py
    -> dist/ETABSLoadAssigner.exe
"""
import PyInstaller.__main__

PyInstaller.__main__.run([
    "main.py",
    "--name", "ETABSLoadAssigner",
    "--onefile",
    "--windowed",
    "--clean",
])
