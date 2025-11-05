# Video Music Converter ✨

![Static Badge](https://img.shields.io/badge/license-MIT-brightgreen?label=LICENSE)

A simple application to extract audio as MP3 from video files (MP4/MKV/AVI/MOV, etc.).

## Installation with `uv` (Windows)

1) **Install uv** (PowerShell):
```powershell
iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
```
Then close and reopen PowerShell/Terminal.

2) **Install Python via uv** (optional, if not already installed):
```powershell
uv python install 3.12
```

3) **Navigate to the project folder** and install dependencies:
```powershell
uv sync
```

4) **Run for testing (without building exe first):**
```powershell
uv run python app.py
```

## Build to .exe (Single File)

```bash
uv add --dev pyinstaller
```

```bash
uv run pyinstaller --noconsole --onefile \
  --name VideoMusicConverter app.py \
  --collect-binaries imageio_ffmpeg \
  --hidden-import tkinterdnd2 \
  --icon assets/icon.ico \
  --add-data 'assets/icon.ico;assets'
```

```powershell
uv run pyinstaller --noconsole --onefile `
  --name VideoMusicConverter app.py `
  --collect-binaries imageio_ffmpeg `
  --hidden-import tkinterdnd2 `
  --icon assets\icon.ico `
  --add-data "assets\icon.ico;assets"
```

---

## License

The code is licensed [MIT](LICENSE)