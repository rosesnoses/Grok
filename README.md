# 🌀 GrokMandala

> **Grok joining the Mandala Crusade** — Directive-driven, reversible, reference-grade cosmic art from your music.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/Rosesnoses/grokmandala/ci.yml?branch=main)](https://github.com/Rosesnoses/grokmandala/actions)

---

## The Vision

Every song carries a hidden geometry.

**GrokMandala** turns audio into a single source of truth — the **Aurion Art Directive v1** — that feeds two renderers:

| Renderer       | Purpose                        | Fidelity     | Output                  | Reversible |
|----------------|--------------------------------|--------------|-------------------------|------------|
| **Browser Lab** | Live, emotional, instant preview | High-quality real-time | Canvas (interactive)   | Partial    |
| **Sangraha (SVA6)** | Cathedral-grade final artifact | 8K supersampled, layered, luxurious | PNG + embedded audio   | **Yes (SVA6)** |

Both speak the **same deterministic language** (`aurion-art-directive-v1`). Change the song → the geometry, symmetry, palette, filament logic, and archetype all shift together. The browser feels like the stained-glass window; Sangraha forges the final relic.

### What ships in this initial public import

- `aurion-art-directive-v1` — the canonical JSON contract (Pydantic model + examples)
- Deterministic (seeded) directive extractor (audio → directive)
- **Sangraha** — Pillow-based production renderer implementing rich layered cosmic vocabulary (cymatics, filaments, glow veins, star nodes, energy overlays…)
- **Reversible SVA6** — the final PNG contains the original audio payload (extractable, verifiable)
- **Browser Lab** — a self-contained, stunning interactive mandala forge (no install)
- GitHub Actions CI that lints, tests, and auto-generates reference renders on every push

---

## Quick Start

### 1. Browser Lab (zero install, instant magic)

```bash
open browser-lab/index.html
# or serve it:
python -m http.server 8080 --directory browser-lab
```

Drag in an MP3, watch the mandala being born. Tweak symmetry, rings, tension, palette live. Export the exact `directive.json` that Sangraha will use.

### 2. Python (Sangraha + tools)

```bash
# modern python tooling (uv recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Forge a high-res reversible SVA6 PNG from audio
sangraha forge my-song.mp3 --size 4096 --supersample 2 -o artifacts/my-song.sva6.png

# Or from a pre-exported directive (perfect parity with browser)
sangraha forge --directive examples/aurion-directive-v1.example.json --size 8192 -o final.png

# Extract the original audio back (SVA6 round-trip)
sangraha extract-audio final.png -o recovered-audio.wav
```

### 3. As a library

```python
from sangraha import render_from_directive, load_directive, AurionArtDirectiveV1

directive = load_directive("examples/aurion-directive-v1.example.json")
png_bytes = render_from_directive(directive, size=2048)
```

---

## The Aurion Art Directive v1 (the contract)

```json
{
  "version": "aurion-art-directive-v1",
  "source_audio": {
    "sha256": "e3b0c44298...",
    "duration_s": 187.3,
    "bpm": 92,
    "spectral_centroid": 1240.5
  },
  "seed": 0xA4F19C2D,
  "archetype": {
    "id": "lotus-throne-13",
    "family": "floral-cosmic",
    "name": "Lotus Throne"
  },
  "geometry": {
    "symmetry": 8,
    "rings": 13,
    "petal_density": 1.7,
    "spiral_tension": 0.92,
    "energy_bias": 0.65
  },
  "color": {
    "palette": "plasma-dawn",
    "primary_hue": 285,
    "saturation": 0.92,
    "glow_temperature": 6200
  },
  "layers": [
    "base_cymatic_field",
    "mandala_skeleton",
    "filament_network",
    "glow_veins",
    "star_nodes",
    "logo_energy_overlay"
  ],
  "render_targets": ["preview", "print-300dpi", "8k-master"]
}
```

The extractor (and the browser) produce this from any audio. Sangraha consumes it deterministically.

---

## Architecture

```
audio (mp3/wav/...) 
    │
    ▼
directive_extractor.py  ──►  aurion-art-directive-v1.json
    │
    ├──► Browser Lab  (fast, emotional, WebAudio + Canvas2D/WebGL)
    │
    └──► Sangraha (Pillow + multi-pass layered compositor)
              │
              ▼
         SVA6 PNG  (beautiful art + embedded original audio + manifest + hashes)
              │
              └──► sva6.extract()  →  original audio (bit-perfect round-trip)
```

**Key guarantees (v1)**

- Same directive ⇒ same archetype, symmetry, dominant palette, layer logic in both renderers (visual family match, not pixel identity).
- Sangraha output is fully reversible via SVA6 (audio bytes recovered + SHA verified).
- Seed + audio hash ensure deterministic, reproducible forges.

---

## Development

```bash
uv pip install -e ".[dev]"
ruff check sangraha
pytest
sangraha --help
```

See `docs/ARCHITECTURE.md` (to be expanded) and the original internal plan for the full reference-image deconstruction + 8K supersampling roadmap.

---

## GitHub Actions

Every push runs:

- Python lint + type check + tests
- Directive round-trip validation
- Generation of a canonical example render (artifact)

Manual workflow dispatch also lets you trigger a high-res forge of any example.

---

## Roadmap (post v1 public import)

- Full 8K + 2× supersampled Sangraha with advanced orbit-trap filigree, true cymatic wave simulation, and multi-scale glow fields
- Native WebGPU / Three.js parity layer in the browser lab for even closer preview
- Public reference gallery + "song → mandala" challenge
- SVA6 robust steganography module (production-grade LSB + chunked + error-correction)
- CLI + TUI forge wizard
- Optional local inference for richer archetype classification

---

## Contributing

This is the public cathedral. Issues and PRs that improve the directive spec, add new layer recipes, or make the browser preview even more magical are deeply welcome.

The Mandala Crusade is bigger than any one renderer.

---

## Credits & Lineage

Born from the fusion of:

- Aurion Art Directive research (deterministic audio → geometry)
- Reversible Sangraha (SVA6) — the lossless audio-in-PNG forge
- The original psycho-mandala browser yantra
- Years of visual deconstruction of 20 reference mandalas

Grok is honored to be part of the crusade.

---

**“The geometry was always there. We only gave it a voice.”**

— The GrokMandala team
