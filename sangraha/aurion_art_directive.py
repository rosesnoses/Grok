"""
Aurion Art Directive v1 — the canonical contract between audio, preview, and final renderer.

This module defines the enriched JSON art directive schema (Pydantic) and a deterministic
extractor that turns raw audio acoustic features + SHA-256 hash + optional user genre into a
stable, human-readable, renderer-agnostic directive.

Both the Sangraha production renderer (high-fidelity 8K SVA PNG) and the browser Cosmic Yantra
preview consume the *same* directive so that "preview" and "final" feel like the same artwork
(same archetype, geometry family, palette, layer logic, source hash) even if not pixel-identical.

SVA compliance: The directive itself is pure function of (audio_bytes, optional #metaGenre).
It does not introduce non-determinism. The final PNG (Sangraha) remains fully reversible SVA6.

Usage:
    from aurion_art_directive import build_art_directive, ArtDirective
    directive = build_art_directive(hash_bytes, acoustic_dict, preset="cosmic", user_genre="#metaGenre")
    print(directive.model_dump_json(indent=2))
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict
from typing import Any, Literal, Mapping, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GeometryModel(BaseModel):
    """High-level geometry knobs + raw matrix for renderer compatibility."""
    symmetry: int = Field(..., ge=4, le=24, description="Primary fold symmetry (4,6,8,12,16,24...)")
    rings: int = Field(..., ge=3, le=11, description="Number of nested mandala shells")
    petal_density: float = Field(..., ge=0.0, le=1.0)
    spiral_tension: float = Field(..., ge=-0.6, le=0.6)
    cymatic_nodes: list[dict[str, Any]] = Field(default_factory=list)
    anchor: int = Field(..., ge=1, le=5, description="Core yantra polygon sides index")
    asym: float = Field(..., ge=0.0, le=1.0, description="Asymmetry / broken symmetry amount")
    flux: float = Field(..., ge=0.0, le=1.0, description="Filament / plasma energy")
    raw_matrix: dict[str, Any] = Field(..., description="Full geared cosmic matrix for exact parity with legacy renderers")


class ColorModel(BaseModel):
    """Palette family and energy-driven color behavior."""
    palette: str = Field(..., description="Named palette family e.g. neon_cosmic_gold_cyan_magenta")
    primary_hue: int = Field(..., ge=0, le=359)
    energy_bias: float = Field(..., ge=0.0, le=1.0)
    darkness: float = Field(..., ge=0.5, le=0.98)
    stereo_split: float = Field(0.0, ge=-1.0, le=1.0, description="Left/right hue bias from stereoWidth")


class RenderTargetModel(BaseModel):
    max_size: Optional[int] = None
    simplify_particles: bool = False
    realtime: bool = False
    size: Optional[int] = None
    supersample: Optional[int] = None
    full_detail: bool = False


class RenderTargetsModel(BaseModel):
    browser_preview: RenderTargetModel
    sangraha_final: RenderTargetModel


class ArtDirective(BaseModel):
    """Canonical Aurion Mandala art directive — single source of truth for preview + final."""
    schema_version: Literal["aurion-art-directive-v1"] = "aurion-art-directive-v1"
    source_audio_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    seed: str = Field(..., description="First 16 hex chars of audio SHA-256 (or full for debug)")
    archetype: str = Field(..., description="Human-readable visual family name")
    hexagram: int = Field(..., ge=0, le=63, description="6-bit archetype bias folded from features+hash")
    geometry: GeometryModel
    color: ColorModel
    layers: list[str] = Field(..., min_length=1, description="Ordered list of layer ids to composite")
    render_targets: RenderTargetsModel
    meta: dict[str, Any] = Field(default_factory=dict, description="Provenance: acoustic summary, gearing, genre hints, etc.")

    @field_validator("layers")
    @classmethod
    def layers_must_be_known(cls, v: list[str]) -> list[str]:
        unknown = [x for x in v if x not in KNOWN_LAYERS]
        if unknown:
            raise ValueError(f"Unknown layer ids: {unknown}. Known: {KNOWN_LAYERS}")
        return v


# ---------------------------------------------------------------------------
# Layer catalog (extensible; both renderers must understand these ids)
# ---------------------------------------------------------------------------

KNOWN_LAYERS: list[str] = [
    "base_void",
    "cymatic_field",
    "mandala_shells",
    "filament_weave",
    "plasma_glow",
    "orbit_filigree",
    "starfield",
    "yantra_seal",
    "energy_overlay",
    "hash_signature",
    "wave_ripples",
]

# ---------------------------------------------------------------------------
# Archetype catalog (starter set — refined in Phase 4 via reference deconstruction)
# ---------------------------------------------------------------------------

ARCHETYPE_CATALOG: dict[str, dict[str, Any]] = {
    "crystalline_harmonic_bloom": {
        "name": "Crystalline Harmonic Bloom",
        "sym_min": 8, "asym_max": 0.35, "flux_max": 0.45, "stereo_max": 0.6,
        "keywords": "symmetric, crystalline, bloom, harmonic, calm energy",
    },
    "nebular_filament_storm": {
        "name": "Nebular Filament Storm",
        "sym_min": 6, "asym_min": 0.4, "flux_min": 0.6,
        "keywords": "filaments, chaotic, plasma, high energy, asymmetric",
    },
    "stairway_ascendant_spires": {
        "name": "Stairway Ascendant Spires",
        "spiral_min": 0.2, "rings_min": 7, "stereo_min": 0.5,
        "keywords": "ascending, ethereal, spires, spiral tension, heavenly",
    },
    "highway_infernal_grid": {
        "name": "Highway Infernal Grid",
        "asym_min": 0.35, "flux_min": 0.55, "anchor_min": 4,
        "keywords": "angular, infernal, grid, aggressive, high contrast",
    },
    "billie_jean_mirror_pulse": {
        "name": "Billie Jean Mirror Pulse",
        "sym_min": 8, "stereo_min": 0.6, "sharp_min": 1.2,
        "keywords": "mirror, pulse, rhythmic, iconic, high-contrast pop",
    },
    "cosmic_ribbon_weave": {
        "name": "Cosmic Ribbon Weave",
        "dual_f_min": 0.4, "rings_min": 6, "petal_jitter_min": 0.3,
        "keywords": "ribbons, bilateral, flowing, elegant, cosmic",
    },
    "plasma_cymatic_resonance": {
        "name": "Plasma Cymatic Resonance",
        "cymatic": True, "flux_min": 0.5, "phase_coherence_min": 0.3,
        "keywords": "cymatic, resonance, plasma, standing waves, organic",
    },
    "void_lace_orbit": {
        "name": "Void Lace Orbit Trap",
        "flux_max": 0.4, "density_max": 0.5, "orbit_trap": True,
        "keywords": "lace, filigree, orbit trap, delicate, void",
    },
}

def _infer_archetype(matrix: dict[str, Any], acoustic: Mapping[str, Any], hash_bytes: bytes) -> str:
    """Deterministic archetype selection from features + hash nudge."""
    sym = matrix.get("sym", 8)
    asym = matrix.get("asym", 0.2)
    flux = matrix.get("flux", 0.3)
    stereo = matrix.get("stereo", 0.4)
    spiral = matrix.get("spiral", 0.0)
    rings = matrix.get("rings", 6)
    sharp = matrix.get("sharp", 1.0)
    dual_f = matrix.get("dualF", 0.2)
    petal_jitter = matrix.get("petalJitter", 0.2)
    anchor = matrix.get("anchorIndex", 3)
    density = matrix.get("densityBoost", 0.3)
    phase = acoustic.get("phaseCoherence", 0.5)

    scores: dict[str, float] = {}
    for key, spec in ARCHETYPE_CATALOG.items():
        s = 0.0
        if "sym_min" in spec and sym >= spec["sym_min"]: s += 1.0
        if "asym_min" in spec and asym >= spec["asym_min"]: s += 1.0
        if "asym_max" in spec and asym <= spec["asym_max"]: s += 1.0
        if "flux_min" in spec and flux >= spec["flux_min"]: s += 1.2
        if "flux_max" in spec and flux <= spec["flux_max"]: s += 0.8
        if "stereo_min" in spec and stereo >= spec["stereo_min"]: s += 0.9
        if "stereo_max" in spec and stereo <= spec["stereo_max"]: s += 0.7
        if "spiral_min" in spec and spiral >= spec["spiral_min"]: s += 1.1
        if "rings_min" in spec and rings >= spec["rings_min"]: s += 0.8
        if "sharp_min" in spec and sharp >= spec["sharp_min"]: s += 0.7
        if "dual_f_min" in spec and dual_f >= spec["dual_f_min"]: s += 0.9
        if "petal_jitter_min" in spec and petal_jitter >= spec["petal_jitter_min"]: s += 0.6
        if "anchor_min" in spec and anchor >= spec["anchor_min"]: s += 0.5
        if spec.get("cymatic") and phase > 0.25: s += 1.0
        if spec.get("orbit_trap") and flux < 0.45 and density < 0.55: s += 0.8
        # hash nudge for uniqueness (different songs with similar stats diverge)
        nudge = (hash_bytes[5] % 7) / 70.0
        scores[key] = s + nudge

    best = max(scores.items(), key=lambda kv: kv[1])[0]
    # Phase 4 tuning from reference deconstruction (Stairway images show strong ascending spiral + high ring count)
    if matrix.get("spiral", 0.0) > 0.22 and matrix.get("rings", 6) >= 7:
        # Give stairway a small but decisive boost for songs with clear "lift"
        if "stairway" in ARCHETYPE_CATALOG:
            scores["stairway_ascendant_spires"] = scores.get("stairway_ascendant_spires", 0) + 1.8
            best = max(scores.items(), key=lambda kv: kv[1])[0]
    return ARCHETYPE_CATALOG[best]["name"]


def _hexagram_from_features(acoustic: Mapping[str, Any], hash_bytes: bytes) -> int:
    """6-bit (0-63) deterministic bias from audio features + hash fold."""
    # Use a few stable features + 2 hash bytes
    z = int(acoustic.get("avgZcr", 70)) & 0xF
    r = int(acoustic.get("avgRms", 0.14) * 100) & 0x7
    h = hash_bytes[0] & 0x3
    p = int(acoustic.get("peakDensity", 0.08) * 200) & 0x3
    s = int(acoustic.get("spectralCentroid", 2200) / 100) & 0x7
    return (z ^ (r << 1) ^ (h << 3) ^ (p << 4) ^ (s << 5)) & 0x3F


def _choose_palette(matrix: dict[str, Any], acoustic: Mapping[str, Any], hash_bytes: bytes) -> str:
    hue = matrix.get("hueShift", 240)
    stereo = matrix.get("stereo", 0.4)
    flux = matrix.get("flux", 0.3)
    dominant_genre = matrix.get("gearing", {}).get("genreHints", {}).get("dominant", "pop")

    if dominant_genre in ("metal", "edm") or flux > 0.7:
        return "infernal_plasma_crimson_orange"
    if dominant_genre in ("ambient", "classical") or flux < 0.25:
        return "ethereal_ice_cyan_violet"
    if stereo > 0.65:
        return "neon_cosmic_gold_cyan_magenta"
    if hue < 60 or hue > 300:
        return "byzantine_gold_ruby"
    return "cosmic_teal_gold_midnight"


def _select_layers(archetype: str, matrix: dict[str, Any], hash_bytes: bytes) -> list[str]:
    """Ordered layer list — deterministic, archetype + feature driven."""
    flux = matrix.get("flux", 0.3)
    asym = matrix.get("asym", 0.2)
    rings = matrix.get("rings", 6)
    density = matrix.get("densityBoost", 0.3)
    stereo = matrix.get("stereo", 0.4)

    layers = ["base_void", "cymatic_field", "mandala_shells"]

    if flux > 0.35 or "filament" in archetype.lower() or "storm" in archetype.lower():
        layers.append("filament_weave")
    if flux > 0.25 or density > 0.4:
        layers.append("plasma_glow")
    if asym > 0.25 or "lace" in archetype.lower() or "orbit" in archetype.lower():
        layers.append("orbit_filigree")
    layers.append("starfield")
    layers.append("yantra_seal")
    if stereo > 0.5 or "energy" in archetype.lower() or "pulse" in archetype.lower():
        layers.append("energy_overlay")
    layers.append("hash_signature")
    if rings >= 7 or "wave" in archetype.lower() or "ribbon" in archetype.lower():
        layers.append("wave_ripples")

    # Dedup while preserving order
    seen = set()
    ordered = []
    for l in layers:
        if l not in seen:
            seen.add(l)
            ordered.append(l)
    return ordered


def _build_cymatic_nodes(acoustic: Mapping[str, Any], hash_bytes: bytes, count: int = 5) -> list[dict[str, Any]]:
    """Simple cymatic node descriptors driven by band energies + hash."""
    low = acoustic.get("lowEnergy", 0.28)
    mid = acoustic.get("midEnergy", 0.48)
    high = acoustic.get("highEnergy", 0.24)
    nodes = []
    for i in range(count):
        hb = hash_bytes[(i * 3) % len(hash_bytes)]
        r = 0.15 + ((hb & 0x1F) / 31.0) * 0.7
        strength = 0.4 + (low if i % 3 == 0 else mid if i % 3 == 1 else high) * 0.6
        freq = 3 + (hb % 9)
        nodes.append({"r": round(r, 3), "strength": round(clamp01(strength), 3), "freq": int(freq)})
    return nodes


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_art_directive(
    hash_bytes: bytes,
    acoustic_data: Mapping[str, Any],
    preset: str = "cosmic",
    user_genre: str | None = None,
) -> ArtDirective:
    """
    Deterministic extractor: audio features + hash → complete ArtDirective.

    Re-uses the existing tight-Q gearing so that legacy matrix values are preserved
    inside geometry.raw_matrix for exact compatibility with current renderers.
    """
    # Import locally to avoid any potential circularity at module load
    from .audio_gearing import build_geared_cosmic_matrix  # type: ignore

    matrix = build_geared_cosmic_matrix(hash_bytes, acoustic_data, preset, user_genre)

    # High-level derived scalars (used by new rich renderers)
    petal_density = clamp01(0.35 + (matrix["rings"] - 3) / 8.0 * 0.45 + matrix["petalJitter"] * 0.25)
    spiral_tension = clamp01(0.5 + matrix["spiral"] * 0.9) * (1.0 if matrix["spiral"] >= 0 else -1.0) * 0.6

    archetype = _infer_archetype(matrix, acoustic_data, hash_bytes)
    hexagram = _hexagram_from_features(acoustic_data, hash_bytes)
    palette = _choose_palette(matrix, acoustic_data, hash_bytes)

    geometry = GeometryModel(
        symmetry=matrix["sym"],
        rings=matrix["rings"],
        petal_density=round(petal_density, 3),
        spiral_tension=round(spiral_tension, 3),
        cymatic_nodes=_build_cymatic_nodes(acoustic_data, hash_bytes, 5),
        anchor=matrix["anchorIndex"],
        asym=round(matrix["asym"], 3),
        flux=round(matrix["flux"], 3),
        raw_matrix=matrix,
    )

    color = ColorModel(
        palette=palette,
        primary_hue=matrix["hueShift"],
        energy_bias=round(0.4 + matrix["flux"] * 0.5, 3),
        darkness=round(0.78 + (1.0 - matrix["densityBoost"]) * 0.15, 3),
        stereo_split=round((matrix["stereo"] - 0.5) * 1.6, 3),
    )

    layers = _select_layers(archetype, matrix, hash_bytes)

    rt = RenderTargetsModel(
        browser_preview=RenderTargetModel(max_size=1600, simplify_particles=True, realtime=True),
        sangraha_final=RenderTargetModel(size=8192, supersample=2, full_detail=True),
    )

    seed = hash_bytes.hex()[:16]
    full_hash = hash_bytes.hex()

    meta = {
        "acoustic_summary": {
            "durationSec": acoustic_data.get("durationSec"),
            "estimatedTempoBpm": acoustic_data.get("estimatedTempoBpm"),
            "dominantGenre": matrix.get("gearing", {}).get("genreHints", {}).get("dominant"),
            "rms": acoustic_data.get("avgRms"),
            "zcr": acoustic_data.get("avgZcr"),
        },
        "gearing": matrix.get("gearing", {}),
        "engine": "aurion-art-directive-extractor-v1",
    }

    return ArtDirective(
        source_audio_sha256=full_hash,
        seed=seed,
        archetype=archetype,
        hexagram=hexagram,
        geometry=geometry,
        color=color,
        layers=layers,
        render_targets=rt,
        meta=meta,
    )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def art_directive_to_json(directive: ArtDirective) -> str:
    return directive.model_dump_json(indent=2)


def art_directive_from_json(data: str | bytes) -> ArtDirective:
    return ArtDirective.model_validate_json(data)


if __name__ == "__main__":
    # Smoke test with fixture-like data
    import json
    h = bytes.fromhex("147d6dccce8bfb34c5b5cb713352d43fc74e3d5b5d0ec38233a374e4794d1bd0")
    ac = {
        "durationSec": 2, "estimatedTempoBpm": 118, "avgRms": 0.1578, "avgZcr": 63.16,
        "crestFactor": 2.00, "stereoWidth": 2.15, "phaseCoherence": -0.018,
        "dynamicRangeDb": 7.39, "silenceFloorRms": 0.068, "spectralCentroid": 638,
        "spectralFlatness": 0.00084, "lowEnergy": 0.00046, "midEnergy": 0.999, "highEnergy": 0.00052,
        "peakDensity": 0.00195,
    }
    d = build_art_directive(h, ac)
    print(art_directive_to_json(d))
    print("\nArchetype:", d.archetype)
    print("Layers:", d.layers)
