"""Sangraha — the reversible high-fidelity mandala renderer (SVA6).

Given an AurionArtDirectiveV1 (or audio path), produces a luxurious, layered, supersampled PNG
that belongs to the same visual family as the browser-lab preview, then embeds the source
audio for perfect round-trip recovery (SVA6 contract).

v1 implementation uses Pillow + deterministic seeded drawing. Future versions will add
true cymatic wave solvers, 8K supersampling, and production steganography.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, PngImagePlugin

from .aurion_art_directive import AurionArtDirectiveV1, LayerName


def _seeded_rng(seed: int) -> random.Random:
    rng = random.Random(seed)
    return rng


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    """Simple HSL to RGB (0-360, 0-1, 0-1) → (0-255, 0-255, 0-255)."""
    h = h % 360
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = l - c / 2
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)


def _palette(directive: AurionArtDirectiveV1) -> dict[str, tuple[int, int, int]]:
    h = directive.color.primary_hue
    s = directive.color.saturation
    return {
        "bg": _hsl_to_rgb(h + 180, s * 0.3, 0.06),
        "ring": _hsl_to_rgb(h, s, 0.92),
        "petal": _hsl_to_rgb(h - 15, s, 0.78),
        "filament": _hsl_to_rgb(h + 25, min(1.0, s + 0.1), 0.85),
        "glow": _hsl_to_rgb(h + 40, 0.6, 0.65),
        "star": (255, 255, 240),
        "energy": _hsl_to_rgb((h + 80) % 360, 0.9, 0.8),
    }


def _draw_cymatic_base(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict) -> None:
    """Organic cymatic rings — the foundation."""
    rings = directive.geometry.rings
    for i in range(rings):
        rr = int(r * (0.15 + 0.85 * (i + 1) / (rings + 1)))
        # Subtle radial modulation for "living" cymatics
        points = []
        steps = 180
        for a in range(steps):
            angle = (a / steps) * 2 * math.pi
            wave = 0.012 * math.sin(6 * angle + i) + 0.007 * math.sin(13 * angle + rng.random())
            rad = rr * (1 + wave)
            x = cx + rad * math.cos(angle)
            y = cy + rad * math.sin(angle)
            points.append((x, y))
        alpha = 40 + int(80 * (i / rings))
        color = (*pal["ring"][:3], alpha)
        draw.polygon(points, outline=color, width=1)

        # Occasional nodal highlights
        if i % 3 == 0:
            for k in range(directive.geometry.symmetry * 2):
                ang = (k / (directive.geometry.symmetry * 2)) * 2 * math.pi
                nx = cx + rr * 0.98 * math.cos(ang)
                ny = cy + rr * 0.98 * math.sin(ang)
                draw.ellipse([nx-1, ny-1, nx+1, ny+1], fill=pal["star"])


def _draw_skeleton(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict) -> None:
    sym = directive.geometry.symmetry
    rings = directive.geometry.rings
    for i in range(rings):
        rr = int(r * (0.12 + 0.88 * (i + 1) / (rings + 1)))
        for k in range(sym):
            ang = (k / sym) * 2 * math.pi
            x2 = cx + rr * math.cos(ang)
            y2 = cy + rr * math.sin(ang)
            draw.line([(cx, cy), (x2, y2)], fill=(*pal["ring"], 70), width=1)


def _draw_filaments(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict) -> None:
    """Intricate filament network — the soul of the piece."""
    sym = directive.geometry.symmetry
    density = directive.geometry.petal_density
    tension = directive.geometry.spiral_tension
    count = int(18 * density)

    for i in range(count):
        phase = (i / count) * 2 * math.pi
        # Primary radial filament
        length = r * (0.35 + 0.55 * rng.random())
        x2 = cx + length * math.cos(phase)
        y2 = cy + length * math.sin(phase)
        w = 1 if rng.random() > 0.7 else 2
        draw.line([(cx, cy), (x2, y2)], fill=(*pal["filament"], 35 + rng.randint(0, 40)), width=w)

        # Spiral / orbiting sub-filaments
        if rng.random() < 0.6:
            cx2, cy2 = x2, y2
            curl = 2.2 * tension
            pts = [(cx2, cy2)]
            for t in range(1, 7):
                ang = phase + t * 0.6 * curl * (1 if i % 2 == 0 else -1)
                rad = length * (0.12 + 0.07 * t)
                pts.append((cx2 + rad * math.cos(ang), cy2 + rad * math.sin(ang)))
            draw.line(pts, fill=(*pal["filament"], 25), width=1)

    # Cross-connections (constellations)
    for _ in range(int(12 * density)):
        a1, a2 = rng.random() * 2 * math.pi, rng.random() * 2 * math.pi
        rad1 = r * (0.2 + 0.7 * rng.random())
        rad2 = r * (0.2 + 0.7 * rng.random())
        p1 = (cx + rad1 * math.cos(a1), cy + rad1 * math.sin(a1))
        p2 = (cx + rad2 * math.cos(a2), cy + rad2 * math.sin(a2))
        draw.line([p1, p2], fill=(*pal["filament"], 12), width=1)


def _draw_glow_veins(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict, img: Image.Image) -> None:
    """Soft glowing veins and energy rivers (multi-pass blur)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    sym = directive.geometry.symmetry
    for k in range(sym * 3):
        ang = (k / (sym * 3)) * 2 * math.pi + rng.uniform(-0.08, 0.08)
        length = r * (0.45 + rng.random() * 0.4)
        x2 = cx + length * math.cos(ang)
        y2 = cy + length * math.sin(ang)
        odraw.line([(cx, cy), (x2, y2)], fill=(*pal["glow"], 18), width=6)
    # Heavy gaussian blur for the ethereal glow
    blurred = overlay.filter(ImageFilter.GaussianBlur(radius=18))
    img.paste(Image.alpha_composite(img, blurred), (0, 0))


def _draw_star_nodes(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict) -> None:
    sym = directive.geometry.symmetry
    rings = directive.geometry.rings
    for i in range(rings):
        rr = int(r * (0.18 + 0.82 * (i + 1) / (rings + 1)))
        for k in range(sym):
            ang = (k / sym) * 2 * math.pi + rng.uniform(-0.03, 0.03)
            x = cx + rr * math.cos(ang)
            y = cy + rr * math.sin(ang)
            size = 1.5 + rng.random() * 2.5
            draw.ellipse([x-size, y-size, x+size, y+size], fill=pal["star"])
            # tiny halo
            draw.ellipse([x-size*2.2, y-size*2.2, x+size*2.2, y+size*2.2], outline=(*pal["star"], 30))


def _draw_energy_overlay(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, directive: AurionArtDirectiveV1, rng: random.Random, pal: dict) -> None:
    """Central energy core / logo signature."""
    core_r = int(r * 0.08)
    for i in range(5, 0, -1):
        rr = int(core_r * (i / 3.5))
        alpha = 40 + i * 18
        draw.ellipse(
            [cx-rr, cy-rr, cx+rr, cy+rr],
            fill=(*pal["energy"], alpha),
        )
    # Small inner sigil
    draw.ellipse([cx-2, cy-2, cx+2, cy+2], fill=pal["star"])


def render_from_directive(
    directive: AurionArtDirectiveV1 | dict[str, Any],
    *,
    size: int = 2048,
    supersample: int = 1,
    return_image: bool = False,
) -> bytes | Image.Image:
    """Render a beautiful layered mandala PNG bytes (or PIL Image) from a directive.

    The output is deterministic for a given directive + size.
    """
    if isinstance(directive, dict):
        directive = AurionArtDirectiveV1.model_validate(directive)

    rng = _seeded_rng(directive.seed)
    render_size = size * max(1, supersample)
    img = Image.new("RGBA", (render_size, render_size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    cx = cy = render_size // 2
    r = int(render_size * 0.48)

    pal = _palette(directive)

    # Background
    img.paste(pal["bg"], (0, 0))

    layers = set(directive.layers)

    if LayerName.BASE_CYMATICS in layers:
        _draw_cymatic_base(draw, cx, cy, r, directive, rng, pal)
    if LayerName.SKELETON in layers:
        _draw_skeleton(draw, cx, cy, r, directive, rng, pal)
    if LayerName.FILAMENTS in layers:
        _draw_filaments(draw, cx, cy, r, directive, rng, pal)
    if LayerName.GLOW_VEINS in layers:
        _draw_glow_veins(draw, cx, cy, r, directive, rng, pal, img)
        draw = ImageDraw.Draw(img, "RGBA")  # re-acquire after paste
    if LayerName.STAR_NODES in layers:
        _draw_star_nodes(draw, cx, cy, r, directive, rng, pal)
    if LayerName.ENERGY_OVERLAY in layers:
        _draw_energy_overlay(draw, cx, cy, r, directive, rng, pal)

    # Gentle vignette for depth
    vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for i in range(12):
        alpha = int(8 * (i + 1))
        vdraw.ellipse(
            [i * 8, i * 8, render_size - i * 8, render_size - i * 8],
            outline=(0, 0, 0, alpha),
        )
    img = Image.alpha_composite(img, vignette)

    # Downsample if supersampled
    if supersample > 1:
        img = img.resize((size, size), Image.Resampling.LANCZOS)

    if return_image:
        return img
    buf = io.BytesIO()
    img_rgb = img.convert("RGB")
    img_rgb.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# SVA6 reversible embedding (v1 contract — text + placeholder binary)
# Full robust audio steganography can be swapped in without changing the public API.
# ──────────────────────────────────────────────────────────────────────────────

SVA6_CHUNK_KEYWORD = b"sVA6"
DIRECTIVE_CHUNK = b"sVA6dir"
AUDIO_CHUNK = b"sVA6aud"


def _png_add_text_chunk(png_bytes: bytes, key: str, value: str) -> bytes:
    """Inject a tEXt chunk into an existing PNG (simple pure-python approach)."""
    # This is a minimal implementation; for production use a proper PNG library.
    # Here we just ensure the directive travels with the image for v1.
    img = Image.open(io.BytesIO(png_bytes))
    meta = PngImagePlugin.PngInfo()
    meta.add_text(key, value, zip=False)
    buf = io.BytesIO()
    img.save(buf, "PNG", pnginfo=meta)
    return buf.getvalue()


def embed_sva6(png_bytes: bytes, directive: AurionArtDirectiveV1, audio_bytes: bytes | None = None) -> bytes:
    """Embed the directive JSON (always) and the original audio (when provided) into the PNG.

    v1 uses PNG tEXt for the directive + a simple side payload marker.
    A future SVA6 module will use custom ancillary chunks + compression + CRC for true bit-perfect audio recovery.
    """
    # Always embed the full directive as text for easy inspection
    directive_json = directive.to_json()
    png_with_dir = _png_add_text_chunk(png_bytes, "sVA6-Directive", directive_json)

    if audio_bytes is None:
        return png_with_dir

    # v1 placeholder: we still ship the audio next to the image for perfect recovery.
    # Real SVA6 will hide it inside the PNG IDAT or custom chunk so the file is self-contained.
    # For now we append a length-prefixed blob after the PNG EOF marker (IEND) — readers must
    # know to look for the sVA6 trailer. This is explicitly marked as transitional.
    trailer = (
        b"\nSVA6v1AUDIO:" +
        len(audio_bytes).to_bytes(4, "big") +
        audio_bytes +
        hashlib.sha256(audio_bytes).digest()
    )
    return png_with_dir + trailer


def extract_audio_from_sva6(sva6_path: str | Path) -> bytes:
    """Recover the embedded audio from an SVA6 artifact (v1 trailer format)."""
    data = Path(sva6_path).read_bytes()
    marker = b"SVA6v1AUDIO:"
    idx = data.find(marker)
    if idx == -1:
        raise ValueError("No SVA6v1 audio trailer found (this PNG may predate full SVA6 embedding)")
    start = idx + len(marker)
    length = int.from_bytes(data[start : start + 4], "big")
    audio = data[start + 4 : start + 4 + length]
    expected_hash = data[start + 4 + length : start + 4 + length + 32]
    if hashlib.sha256(audio).digest() != expected_hash:
        raise ValueError("SVA6 audio hash mismatch — file may be corrupted or tampered")
    return audio


def forge(
    audio_path: str | Path | None = None,
    *,
    directive: AurionArtDirectiveV1 | dict[str, Any] | None = None,
    size: int = 4096,
    supersample: int = 2,
    output: str | Path | None = None,
) -> Path:
    """Convenience one-liner: audio or directive → beautiful reversible SVA6 PNG on disk."""
    if directive is None and audio_path is None:
        raise ValueError("Provide either an audio_path or a directive")

    if directive is None:
        from .directive_extractor import extract_directive

        directive = extract_directive(audio_path)  # type: ignore[arg-type]

    if isinstance(directive, dict):
        directive = AurionArtDirectiveV1.model_validate(directive)

    png_bytes = render_from_directive(directive, size=size, supersample=supersample)

    audio_bytes: bytes | None = None
    if audio_path:
        audio_bytes = Path(audio_path).read_bytes()

    final = embed_sva6(png_bytes, directive, audio_bytes)

    out_path = Path(output) if output else Path(f"{Path(audio_path).stem if audio_path else 'mandala'}-sva6.png")
    out_path.write_bytes(final)
    return out_path
