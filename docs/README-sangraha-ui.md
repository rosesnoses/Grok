# Sangraha Mandala Studio

Sangraha now has a local web UI for the Python fractal/steganography engine.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-sangraha.txt
```

## Run

```bash
python -m uvicorn sangraha_server:app --reload --port 8091
```

Open http://127.0.0.1:8091.

## What It Does

- Forge Mandala: uploads any file, renders a deterministic fractal mandala, embeds the file losslessly, and returns a PNG.
- Recover File: uploads a Sangraha PNG and extracts the hidden payload with the matching passphrase.
- Advanced Geometry: exposes formula, trap, power, symmetry, iteration, size, seed, and auto-size controls.

Generated files are written under `.sangraha_runs/` and served through the UI download links.
