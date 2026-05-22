"""Aurion audio gearing — Python parity with psycho-mandala/audio-gearing.js."""

from __future__ import annotations

import math
from typing import Any, Mapping

SYMMETRIES = [4, 6, 8, 10, 12, 16, 24]

MUSIC_PRIORS: dict[str, dict[str, float]] = {
    "durationSec": {"center": 210, "sigma": 45, "q": 2.4},
    "tempoBpm": {"center": 118, "sigma": 22, "q": 2.2},
    "avgRms": {"center": 0.14, "sigma": 0.045, "q": 2.6},
    "avgZcr": {"center": 72, "sigma": 28, "q": 2.0},
    "crestFactor": {"center": 2.35, "sigma": 0.55, "q": 2.3},
    "stereoWidth": {"center": 0.55, "sigma": 0.35, "q": 2.1},
    "dynamicRangeDb": {"center": 9.5, "sigma": 3.5, "q": 2.4},
    "spectralCentroid": {"center": 2200, "sigma": 900, "q": 2.0},
    "spectralRolloff": {"center": 4800, "sigma": 2200, "q": 2.0},
    "spectralFlatness": {"center": 0.12, "sigma": 0.08, "q": 2.5},
    "phaseCoherence": {"center": 0.55, "sigma": 0.28, "q": 2.2},
    "peakDensity": {"center": 0.08, "sigma": 0.05, "q": 2.3},
    "lowEnergy": {"center": 0.28, "sigma": 0.12, "q": 2.2},
    "midEnergy": {"center": 0.48, "sigma": 0.14, "q": 2.2},
    "highEnergy": {"center": 0.24, "sigma": 0.11, "q": 2.2},
}

GENRE_SIGNATURES: dict[str, dict[str, float]] = {
    "pop": {"centroid": 2400, "flatness": 0.08, "zcr": 85, "crest": 2.2, "tempo": 115, "high": 0.22},
    "hiphop": {"centroid": 900, "flatness": 0.05, "zcr": 55, "crest": 2.8, "tempo": 92, "low": 0.42},
    "edm": {"centroid": 3200, "flatness": 0.15, "zcr": 110, "crest": 2.0, "tempo": 128, "high": 0.35},
    "rock": {"centroid": 2800, "flatness": 0.06, "zcr": 95, "crest": 2.6, "tempo": 122, "mid": 0.52},
    "ambient": {"centroid": 1400, "flatness": 0.22, "zcr": 45, "crest": 1.8, "tempo": 72, "low": 0.35},
    "classical": {"centroid": 1800, "flatness": 0.04, "zcr": 60, "crest": 3.2, "tempo": 96, "dynamic": 16},
    "metal": {"centroid": 3400, "flatness": 0.04, "zcr": 120, "crest": 3.0, "tempo": 138, "high": 0.30},
    "rnb": {"centroid": 1900, "flatness": 0.07, "zcr": 70, "crest": 2.1, "tempo": 88, "low": 0.38},
}

USER_GENRE_ALIASES: dict[str, list[str]] = {
    "pop": ["pop", "dance pop", "synthpop", "k-pop", "j-pop", "top 40"],
    "hiphop": ["hip hop", "hip-hop", "rap", "trap", "drill", "grime"],
    "edm": ["edm", "electronic", "house", "techno", "trance", "dubstep"],
    "rock": ["rock", "alternative", "indie", "punk", "grunge", "alt-rock"],
    "ambient": ["ambient", "new age", "drone", "soundscape"],
    "classical": ["classical", "orchestral", "chamber", "baroque"],
    "metal": ["metal", "heavy metal", "hardcore", "death metal"],
    "rnb": ["r&b", "rnb", "soul", "neo soul", "neo-soul"],
}


def normalize_user_genre(label: str | None) -> str | None:
    text = str(label or "").lower().strip()
    if not text:
        return None
    for key, aliases in USER_GENRE_ALIASES.items():
        if any(alias in text for alias in aliases):
            return key
    return None


def merge_user_genre_hints(inferred: dict[str, Any], user_genre_key: str | None) -> dict[str, Any]:
    if not user_genre_key or user_genre_key not in GENRE_SIGNATURES:
        return inferred
    merged = dict(inferred)
    boost = 0.35
    merged[user_genre_key] = merged.get(user_genre_key, 0.0) + boost
    total = sum(merged.get(key, 0.0) for key in GENRE_SIGNATURES) or 1.0
    for key in GENRE_SIGNATURES:
        merged[key] = merged.get(key, 0.0) / total
    merged["dominant"] = max(GENRE_SIGNATURES, key=lambda k: merged.get(k, 0.0))
    merged["userGenre"] = user_genre_key
    return merged


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def clamp01(v: float) -> float:
    return clamp(v, 0.0, 1.0)


def gear_deviation(value: float, center: float, sigma: float, q: float) -> float:
    z = (value - center) / max(sigma, 1e-9)
    return clamp(math.tanh(z * q), -1.0, 1.0)


def gear_map(deviation: float, out_min: float, out_max: float, emphasis: float) -> float:
    u = (deviation * emphasis + 1.0) * 0.5
    return out_min + clamp01(u) * (out_max - out_min)


def gear_spread(value: float, prior: Mapping[str, float], out_min: float, out_max: float, emphasis: float) -> float:
    d = gear_deviation(value, prior["center"], prior["sigma"], prior["q"])
    return gear_map(d, out_min, out_max, emphasis)


def band_above_silence(energy: float, silence_floor: float) -> float:
    ref = max(silence_floor, 1e-6)
    return clamp01((energy - ref) / max(1.0 - ref, 1e-6))


def hash_unit(hash_bytes: bytes, index: int) -> float:
    return hash_bytes[index % len(hash_bytes)] / 255.0


def infer_genre_hints(acoustic: Mapping[str, Any]) -> dict[str, Any]:
    hints: dict[str, float] = {}
    tempo = acoustic.get("estimatedTempoBpm", MUSIC_PRIORS["tempoBpm"]["center"])
    centroid = acoustic.get("spectralCentroid", MUSIC_PRIORS["spectralCentroid"]["center"])
    flatness = acoustic.get("spectralFlatness", MUSIC_PRIORS["spectralFlatness"]["center"])
    zcr = acoustic.get("avgZcr", MUSIC_PRIORS["avgZcr"]["center"])
    crest = acoustic.get("crestFactor", MUSIC_PRIORS["crestFactor"]["center"])
    low = acoustic.get("lowEnergy", MUSIC_PRIORS["lowEnergy"]["center"])
    mid = acoustic.get("midEnergy", MUSIC_PRIORS["midEnergy"]["center"])
    high = acoustic.get("highEnergy", MUSIC_PRIORS["highEnergy"]["center"])
    dyn = acoustic.get("dynamicRangeDb", MUSIC_PRIORS["dynamicRangeDb"]["center"])

    for name, sig in GENRE_SIGNATURES.items():
        score = 0.0
        if "centroid" in sig:
            score += 1.2 - abs(centroid - sig["centroid"]) / 4000
        if "flatness" in sig:
            score += 1.0 - abs(flatness - sig["flatness"]) / 0.25
        if "zcr" in sig:
            score += 1.0 - abs(zcr - sig["zcr"]) / 120
        if "crest" in sig:
            score += 0.8 - abs(crest - sig["crest"]) / 2.5
        if "tempo" in sig:
            score += 1.1 - abs(tempo - sig["tempo"]) / 80
        if "low" in sig:
            score += 0.7 - abs(low - sig["low"]) / 0.5
        if "mid" in sig:
            score += 0.7 - abs(mid - sig["mid"]) / 0.5
        if "high" in sig:
            score += 0.7 - abs(high - sig["high"]) / 0.5
        if "dynamic" in sig:
            score += 0.9 - abs(dyn - sig["dynamic"]) / 14
        hints[name] = max(0.0, score)

    total = sum(hints.values()) or 1.0
    for key in hints:
        hints[key] /= total

    dominant = max(hints.items(), key=lambda item: item[1])[0]
    return {**hints, "dominant": dominant}


def derive_ring_profile(acoustic: Mapping[str, Any], hash_bytes: bytes, ring_count: int) -> list[dict[str, Any]]:
    silence = acoustic.get("silenceFloorRms", 0.008)
    low = band_above_silence(acoustic.get("lowEnergy", 0.33), silence * 8)
    mid = band_above_silence(acoustic.get("midEnergy", 0.34), silence * 8)
    high = band_above_silence(acoustic.get("highEnergy", 0.33), silence * 8)
    band_sum = low + mid + high or 1.0
    norm = {"low": low / band_sum, "mid": mid / band_sum, "high": high / band_sum}

    profile: list[dict[str, Any]] = []
    for i in range(ring_count):
        t = 0.5 if ring_count <= 1 else i / (ring_count - 1)
        low_w = max(0.0, 1.0 - t * 2.2)
        high_w = max(0.0, (t - 0.35) * 1.8)
        mid_w = max(0.0, 1.0 - abs(t - 0.45) * 2.4)
        weight = low_w * norm["low"] + mid_w * norm["mid"] + high_w * norm["high"]
        hash_n = hash_bytes[(i + 3) % len(hash_bytes)] / 255.0
        sym_bias = round((low_w * 4 + mid_w * 8 + high_w * 12 + hash_n * 4) - 2)
        sharp_bias = clamp01(mid_w * 0.35 + high_w * 0.55 + low_w * 0.15)
        warp_bias = 0.88 + weight * 0.22 + hash_n * 0.08
        profile.append(
            {
                "index": i + 1,
                "radialT": t,
                "weight": clamp01(weight * 1.35),
                "symBias": sym_bias,
                "sharpBias": sharp_bias,
                "warpBias": warp_bias,
                "bandMix": {
                    "low": low_w * norm["low"],
                    "mid": mid_w * norm["mid"],
                    "high": high_w * norm["high"],
                },
            }
        )
    return profile


def derive_ring_count(acoustic: Mapping[str, Any], hash_bytes: bytes, genre_hints: Mapping[str, Any]) -> int:
    silence = acoustic.get("silenceFloorRms", 0.008)
    low = band_above_silence(acoustic.get("lowEnergy", 0.33), silence * 8)
    mid = band_above_silence(acoustic.get("midEnergy", 0.34), silence * 8)
    high = band_above_silence(acoustic.get("highEnergy", 0.33), silence * 8)
    band_spread = 1.0 - max(low, mid, high) / max(low + mid + high, 1e-6)

    rms_dev = gear_deviation(
        acoustic.get("avgRms", 0.14),
        MUSIC_PRIORS["avgRms"]["center"],
        MUSIC_PRIORS["avgRms"]["sigma"],
        MUSIC_PRIORS["avgRms"]["q"],
    )
    dyn_dev = gear_deviation(
        acoustic.get("dynamicRangeDb", 9.5),
        MUSIC_PRIORS["dynamicRangeDb"]["center"],
        MUSIC_PRIORS["dynamicRangeDb"]["sigma"],
        MUSIC_PRIORS["dynamicRangeDb"]["q"],
    )
    dur_dev = gear_deviation(
        acoustic.get("durationSec", 210),
        MUSIC_PRIORS["durationSec"]["center"],
        MUSIC_PRIORS["durationSec"]["sigma"],
        MUSIC_PRIORS["durationSec"]["q"],
    )
    dominant = genre_hints["dominant"]
    genre_spread = 1.0 - float(genre_hints.get(dominant, 0.25))

    composite = (
        band_spread * 0.38
        + ((rms_dev + 1) * 0.5) * 0.22
        + ((dyn_dev + 1) * 0.5) * 0.18
        + ((dur_dev + 1) * 0.5) * 0.12
        + genre_spread * 0.10
    )
    hash_nudge = (hash_bytes[11] % 5) - 2
    return clamp(round(3 + composite * 8 + hash_nudge), 3, 11)


def pick_symmetry(acoustic: Mapping[str, Any], hash_bytes: bytes, genre_hints: Mapping[str, Any]) -> int:
    zcr_dev = gear_deviation(
        acoustic.get("avgZcr", 72),
        MUSIC_PRIORS["avgZcr"]["center"],
        MUSIC_PRIORS["avgZcr"]["sigma"],
        MUSIC_PRIORS["avgZcr"]["q"],
    )
    peak_dev = gear_deviation(
        acoustic.get("peakDensity", 0.08),
        MUSIC_PRIORS["peakDensity"]["center"],
        MUSIC_PRIORS["peakDensity"]["sigma"],
        MUSIC_PRIORS["peakDensity"]["q"],
    )
    genre_idx = {
        "pop": 8,
        "hiphop": 6,
        "edm": 12,
        "rock": 8,
        "ambient": 4,
        "classical": 6,
        "metal": 16,
        "rnb": 6,
    }
    genre_sym = genre_idx.get(genre_hints.get("dominant", "pop"), 8)
    acoustic_sym = acoustic.get("symmetry")
    base_idx = SYMMETRIES.index(acoustic_sym) if acoustic_sym in SYMMETRIES else clamp(
        round(2 + ((zcr_dev + 1) * 0.5) * 4 + peak_dev * 1.5), 0, len(SYMMETRIES) - 1
    )
    genre_target = SYMMETRIES.index(genre_sym)
    blended = clamp(round(base_idx * 0.55 + genre_target * 0.45), 0, len(SYMMETRIES) - 1)
    sym_nudge = (hash_bytes[8] % 3) - 1
    return SYMMETRIES[clamp(blended + sym_nudge, 0, len(SYMMETRIES) - 1)]


def band_spread_from_bands(acoustic: Mapping[str, Any]) -> float:
    low = acoustic.get("lowEnergy", 0.33)
    mid = acoustic.get("midEnergy", 0.34)
    high = acoustic.get("highEnergy", 0.33)
    peak = max(low, mid, high)
    return 1.0 - peak / max(low + mid + high, 1e-6)


def build_geared_cosmic_matrix(
    hash_bytes: bytes,
    acoustic_data: Mapping[str, Any],
    preset: str = "cosmic",
    user_genre: str | None = None,
) -> dict[str, Any]:
    _ = preset  # reserved for preset-specific gearing extensions
    seed_slice = hash_bytes.hex()
    genre_hints = merge_user_genre_hints(
        infer_genre_hints(acoustic_data),
        normalize_user_genre(user_genre),
    )
    rings = derive_ring_count(acoustic_data, hash_bytes, genre_hints)
    ring_profile = derive_ring_profile(acoustic_data, hash_bytes, rings)
    sym = pick_symmetry(acoustic_data, hash_bytes, genre_hints)

    crest_dev = gear_deviation(
        acoustic_data.get("crestFactor", 2.35),
        MUSIC_PRIORS["crestFactor"]["center"],
        MUSIC_PRIORS["crestFactor"]["sigma"],
        MUSIC_PRIORS["crestFactor"]["q"],
    )
    line_energy = gear_map(crest_dev, 0.75, 2.65, 1.15)

    high_dev = gear_deviation(
        acoustic_data.get("highEnergy", 0.24),
        MUSIC_PRIORS["highEnergy"]["center"],
        MUSIC_PRIORS["highEnergy"]["sigma"],
        MUSIC_PRIORS["highEnergy"]["q"],
    )
    peak_dev = gear_deviation(
        acoustic_data.get("peakDensity", 0.08),
        MUSIC_PRIORS["peakDensity"]["center"],
        MUSIC_PRIORS["peakDensity"]["sigma"],
        MUSIC_PRIORS["peakDensity"]["q"],
    )
    flux = clamp01(0.12 + ((high_dev + 1) * 0.5) * 0.55 + ((peak_dev + 1) * 0.5) * 0.38)

    flat_dev = gear_deviation(
        acoustic_data.get("spectralFlatness", 0.12),
        MUSIC_PRIORS["spectralFlatness"]["center"],
        MUSIC_PRIORS["spectralFlatness"]["sigma"],
        MUSIC_PRIORS["spectralFlatness"]["q"],
    )
    dual_f = clamp01(0.05 + ((crest_dev + 1) * 0.5) * 0.35 + ((flat_dev + 1) * 0.5) * 0.45)
    sharp = gear_spread(
        acoustic_data.get("spectralFlatness", 0.12),
        MUSIC_PRIORS["spectralFlatness"],
        0.35,
        1.95,
        1.2,
    )
    sharp_inv = 2.0 - sharp

    phase_dev = gear_deviation(
        acoustic_data.get("phaseCoherence", 0.55),
        MUSIC_PRIORS["phaseCoherence"]["center"],
        MUSIC_PRIORS["phaseCoherence"]["sigma"],
        MUSIC_PRIORS["phaseCoherence"]["q"],
    )
    asym = clamp01(0.08 + ((crest_dev + 1) * 0.5) * 0.42 + ((1 - ((phase_dev + 1) * 0.5)) * 0.55))

    stereo_dev = gear_deviation(
        acoustic_data.get("stereoWidth", 0.55),
        MUSIC_PRIORS["stereoWidth"]["center"],
        MUSIC_PRIORS["stereoWidth"]["sigma"],
        MUSIC_PRIORS["stereoWidth"]["q"],
    )
    stereo = clamp01(0.2 + ((stereo_dev + 1) * 0.5) * 0.75)

    dyn_dev = gear_deviation(
        acoustic_data.get("dynamicRangeDb", 9.5),
        MUSIC_PRIORS["dynamicRangeDb"]["center"],
        MUSIC_PRIORS["dynamicRangeDb"]["sigma"],
        MUSIC_PRIORS["dynamicRangeDb"]["q"],
    )
    anchor_index = clamp(round(3 - dyn_dev * 1.8 + ((hash_bytes[10] % 3) - 1)), 1, 5)

    dur_dev = gear_deviation(
        acoustic_data.get("durationSec", 210),
        MUSIC_PRIORS["durationSec"]["center"],
        MUSIC_PRIORS["durationSec"]["sigma"],
        MUSIC_PRIORS["durationSec"]["q"],
    )
    plasma_feature = clamp01(0.25 + ((phase_dev + 1) * 0.5) * 0.45 + dur_dev * 0.08)

    hue_shift = math.floor(hash_unit(hash_bytes, 12) * 360)
    rotation_offset = hash_unit(hash_bytes, 13) * math.pi * 2
    spiral = gear_map(
        gear_deviation(
            acoustic_data.get("estimatedTempoBpm", 118),
            MUSIC_PRIORS["tempoBpm"]["center"],
            MUSIC_PRIORS["tempoBpm"]["sigma"],
            MUSIC_PRIORS["tempoBpm"]["q"],
        ),
        -0.55,
        0.55,
        1.0,
    ) + (hash_unit(hash_bytes, 14) - 0.5) * 0.25
    layer_warp = 0.88 + hash_unit(hash_bytes, 15) * 0.22 + ((dyn_dev + 1) * 0.5) * 0.08
    petal_jitter = clamp01(0.15 + band_spread_from_bands(acoustic_data) * 0.65 + hash_unit(hash_bytes, 16) * 0.25)
    density_boost = clamp01(0.1 + flux * 0.55 + hash_unit(hash_bytes, 17) * 0.35)
    signature_twist = hash_unit(hash_bytes, 18) * math.pi * 2

    return {
        "seedStr": seed_slice,
        "sym": sym,
        "anchorIndex": anchor_index,
        "rings": rings,
        "ringProfile": ring_profile,
        "lineEnergy": line_energy,
        "flux": flux,
        "dualF": dual_f,
        "sharp": sharp_inv,
        "asym": asym,
        "stereo": stereo,
        "hueShift": hue_shift,
        "rotationOffset": rotation_offset,
        "spiral": spiral,
        "layerWarp": layer_warp,
        "petalJitter": petal_jitter,
        "densityBoost": density_boost,
        "signatureTwist": signature_twist,
        "plasmaFeature": plasma_feature,
        "gearing": {
            "genreHints": genre_hints,
            "durationDev": dur_dev,
            "tempoDev": gear_deviation(
                acoustic_data.get("estimatedTempoBpm", 118),
                MUSIC_PRIORS["tempoBpm"]["center"],
                MUSIC_PRIORS["tempoBpm"]["sigma"],
                MUSIC_PRIORS["tempoBpm"]["q"],
            ),
            "rmsDev": gear_deviation(
                acoustic_data.get("avgRms", 0.14),
                MUSIC_PRIORS["avgRms"]["center"],
                MUSIC_PRIORS["avgRms"]["sigma"],
                MUSIC_PRIORS["avgRms"]["q"],
            ),
        },
    }


def derive_cosmic_matrix(hash_bytes: bytes, acoustic_data: Mapping[str, Any], preset: str = "cosmic") -> dict[str, Any]:
    """Naming parity with psycho-mandala/index.html deriveCosmicMatrix."""
    return build_geared_cosmic_matrix(hash_bytes, acoustic_data, preset)


def to_art_directive(
    hash_bytes: bytes,
    acoustic_data: Mapping[str, Any],
    preset: str = "cosmic",
    user_genre: str | None = None,
) -> dict[str, Any]:
    """
    Canonical entry point for the aurion-art-directive-v1 contract.

    Returns a plain dict (JSON serializable) that both Sangraha (production 8K renderer)
    and the browser preview can consume to produce stylistically consistent output.

    The heavy lifting lives in aurion_art_directive.build_art_directive (Pydantic model).
    This thin wrapper keeps the public gearing API stable and import-light for callers
    that only need the legacy matrix.
    """
    # Local import avoids top-level circular dependency during early bootstrap
    from .aurion_art_directive import build_art_directive  # type: ignore[attr-defined]

    directive_model = build_art_directive(hash_bytes, acoustic_data, preset, user_genre)
    return directive_model.model_dump()
