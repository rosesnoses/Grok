# GrokMandala Architecture (v1 public)

This document captures the core ideas behind the initial public import.

## The Directive Contract

`aurion-art-directive-v1` is the lingua franca.

Everything — browser preview, Sangraha production renderer, future ML archetype classifiers, and even external tools — consumes and produces the same JSON shape.

See `sangraha/aurion_art_directive.py` for the authoritative Pydantic model.

## Two Renderers, One Soul

**Browser Lab** (`browser-lab/index.html`)
- Zero-dependency, self-contained HTML/JS
- Web Audio API + lightweight client feature extraction
- Canvas2D renderer that mirrors the Python layer logic
- Live controls that mutate the directive in real time
- Export button produces byte-for-byte compatible JSON for the CLI

**Sangraha** (Python)
- `sangraha forge` CLI entrypoint
- `render_from_directive()` — Pillow multi-pass layered drawing
- Deterministic via seed + audio SHA
- SVA6 embedding (transitional v1 trailer; production stego planned)

## Reversible SVA6

The goal: a single `.png` file that is:
1. Visually stunning at 4K–8K
2. Contains the complete original audio (bit-perfect)
3. Contains the full directive + hashes for provenance

v1 uses a pragmatic trailer after the PNG IEND for the audio bytes (easy to extract, obvious format).

Future versions will migrate to custom ancillary PNG chunks (`sVA6`, `sVA6aud`, etc.) + compression + forward error correction while keeping the public API identical.

## Extensibility

- New layers can be added to the enum in the directive model and implemented in both renderers.
- Archetype inference lives in `directive_extractor.py` — easy to replace with a small ONNX model later.
- The browser renderer and Python renderer are intentionally kept in sync by sharing the same numeric mapping from features → params.

---

This initial import gives the community the contract and two beautiful, usable implementations. Everything else is iteration toward the cathedral.
