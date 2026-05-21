"""Directive Extractor — audio to Aurion Art Directive v1.

Deterministic pipeline:
  1. Canonical audio bytes → SHA-256 (the single source of truth hash)
  2. Lightweight acoustic features (duration, energy, spectral hints, BPM estimate)
  3. Archetype inference (rule-based v1; ML model can be swapped in later)
  4. Geometry + color mapping from features + stable seed derivation
  5. Emit complete, validated AurionArtDirectiveV1

The extractor is deliberately lightweight for the public v1 import.
Heavy lifting (librosa, etc.) is optional via the [audio] extra.
"""

from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path
from typing import Any

import numpy as np

from .aurion_art_directive import (
    Archetype,
    AurionArtDirectiveV1,
    ColorSpec,
    Geometry,
    LayerName,
    SourceAudio,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _derive_seed(audio_sha: str, salt: str = "aurion-v1") -> int:
    """Stable 32-bit seed from the audio hash + salt (so same audio = same art)."""
    h = hashlib.sha256((audio_sha + salt).encode()).digest()
    return struct.unpack(">I", h[:4])[0]


def _basic_waveform_features(wave: np.ndarray, sr: int) -> dict[str, float]:
    """Pure-numpy fallback features when librosa is unavailable."""
    if len(wave) == 0:
        return {"rms": 0.0, "zcr": 0.0, "centroid": 0.0}

    # RMS
    rms = float(np.sqrt(np.mean(wave**2)))

    # Zero-crossing rate (approximate)
    zcr = float(np.mean(np.abs(np.diff(np.sign(wave)))) / 2)

    # Very rough spectral centroid proxy via FFT magnitude-weighted freq
    fft = np.fft.rfft(wave)
    mag = np.abs(fft)
    freqs = np.fft.rfftfreq(len(wave), 1.0 / sr)
    if mag.sum() > 0:
        centroid = float(np.sum(freqs * mag) / np.sum(mag))
    else:
        centroid = 0.0

    return {"rms": rms, "zcr": zcr, "centroid": centroid}


def _estimate_bpm(wave: np.ndarray, sr: int) -> float | None:
    """Ultra-light BPM guess (autocorrelation of energy envelope). Not production grade."""
    if len(wave) < sr:
        return None
    # Downsample envelope
    hop = sr // 100
    env = np.abs(wave[::hop])
    if len(env) < 20:
        return None
    # Simple autocorrelation peak in plausible BPM range
    ac = np.correlate(env - env.mean(), env - env.mean(), mode="full")
    ac = ac[len(ac) // 2 :]
    # Look for peaks ~ 0.3s – 1.2s (50–200 bpm)
    lag_min, lag_max = int(0.3 * (sr / hop)), int(1.2 * (sr / hop))
    if lag_max >= len(ac):
        return None
    segment = ac[lag_min:lag_max]
    if len(segment) < 3 or segment.max() <= 0:
        return None
    best_lag = int(np.argmax(segment)) + lag_min
    period_s = best_lag * hop / sr
    bpm = 60.0 / period_s
    return float(np.clip(bpm, 40, 220))


def analyze_audio(audio_path: str | Path, *, salt: str = "aurion-v1") -> dict[str, Any]:
    """Return a rich feature dict. Tries librosa when available, otherwise pure numpy fallback."""
    audio_path = Path(audio_path)
    raw = audio_path.read_bytes()
    audio_sha = _sha256(raw)

    # Try optional heavy deps first
    try:
        import librosa  # type: ignore

        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        duration = float(len(y) / sr)
        rms = float(np.sqrt(np.mean(y**2)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        bpm, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.clip(bpm, 40, 220)) if bpm else None
        features = {
            "duration_s": duration,
            "rms_energy": rms,
            "zero_crossing_rate": zcr,
            "spectral_centroid": centroid,
            "bpm": bpm,
        }
    except Exception:
        # Fallback — read as 16-bit PCM if possible (very rough for demo)
        try:
            # Assume 44.1k 16-bit stereo or mono; this is intentionally crude for v1
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            sr = 44100
            if len(data) > 2:
                data = data[::2]  # crude mono
            features = _basic_waveform_features(data, sr)
            features["duration_s"] = len(data) / sr
            features["bpm"] = _estimate_bpm(data, sr)
        except Exception:
            features = {
                "duration_s": 180.0,
                "rms_energy": 0.1,
                "zero_crossing_rate": 0.05,
                "spectral_centroid": 1200.0,
                "bpm": 90.0,
            }

    features["sha256"] = audio_sha
    return {"features": features, "seed": _derive_seed(audio_sha, salt)}


def infer_archetype(features: dict[str, Any]) -> Archetype:
    """Rule-based v1 archetype inference — deterministic and explainable."""
    energy = features.get("rms_energy", 0.1) or 0.1
    centroid = features.get("spectral_centroid", 1000) or 1000
    bpm = features.get("bpm") or 90

    if energy > 0.25 and centroid > 1800:
        return Archetype(id="plasma-storm-7", family="fractal-storm", name="Plasma Storm")
    if bpm > 140:
        return Archetype(id="thunder-lotus-11", family="floral-cosmic", name="Thunder Lotus")
    if centroid < 800:
        return Archetype(id="deep-void-5", family="void-geometry", name="Deep Void")
    # Default elegant cosmic
    return Archetype(id="lotus-throne-13", family="floral-cosmic", name="Lotus Throne")


def build_geometry(features: dict[str, Any], seed: int) -> Geometry:
    """Map acoustic features into stable, pleasing geometry parameters."""
    rng = np.random.default_rng(seed)
    energy = features.get("rms_energy", 0.12) or 0.12
    bpm = features.get("bpm") or 90

    symmetry = int(np.clip(3 + int(energy * 9) + rng.integers(-1, 2), 3, 16))
    rings = int(np.clip(5 + int((bpm - 60) / 12) + rng.integers(-1, 2), 4, 24))
    petal_density = float(np.clip(0.6 + energy * 2.2 + rng.uniform(-0.15, 0.15), 0.4, 4.5))
    spiral_tension = float(np.clip(0.55 + (centroid := features.get("spectral_centroid", 1100) or 1100) / 4500, 0.3, 1.35))
    energy_bias = float(np.clip(0.35 + energy * 0.9, 0.15, 0.95))

    return Geometry(
        symmetry=symmetry,
        rings=rings,
        petal_density=round(petal_density, 2),
        spiral_tension=round(spiral_tension, 2),
        energy_bias=round(energy_bias, 2),
    )


def build_color(features: dict[str, Any], seed: int) -> ColorSpec:
    rng = np.random.default_rng(seed)
    centroid = features.get("spectral_centroid", 1200) or 1200
    energy = features.get("rms_energy", 0.1) or 0.1

    # Hue from centroid (higher = cooler / more violet-blue)
    hue = int((centroid / 35 + rng.uniform(-8, 8)) % 360)
    sat = float(np.clip(0.78 + energy * 0.25, 0.65, 0.98))
    temp = int(4200 + (centroid - 800) * 1.8 + rng.integers(-300, 300))
    return ColorSpec(
        palette="plasma-dawn" if energy < 0.2 else "cosmic-ion",
        primary_hue=hue,
        saturation=round(sat, 2),
        glow_temperature=temp,
    )


def extract_directive(
    audio_path: str | Path,
    *,
    title: str | None = None,
    artist: str | None = None,
    salt: str = "aurion-v1",
) -> AurionArtDirectiveV1:
    """High-level entry point: audio file → fully populated, validated directive."""
    analysis = analyze_audio(audio_path, salt=salt)
    feats = analysis["features"]
    seed = analysis["seed"]

    archetype = infer_archetype(feats)
    geometry = build_geometry(feats, seed)
    color = build_color(feats, seed)

    src = SourceAudio(
        sha256=feats["sha256"],
        duration_s=round(feats["duration_s"], 2),
        bpm=feats.get("bpm"),
        spectral_centroid=feats.get("spectral_centroid"),
        rms_energy=feats.get("rms_energy"),
        zero_crossing_rate=feats.get("zero_crossing_rate"),
    )

    meta: dict[str, str] = {}
    if title:
        meta["title"] = title
    if artist:
        meta["artist"] = artist
    meta["extractor"] = "directive_extractor.py@v1"

    directive = AurionArtDirectiveV1(
        source_audio=src,
        seed=seed,
        archetype=archetype,
        geometry=geometry,
        color=color,
        layers=[
            LayerName.BASE_CYMATICS,
            LayerName.SKELETON,
            LayerName.FILAMENTS,
            LayerName.GLOW_VEINS,
            LayerName.STAR_NODES,
            LayerName.ENERGY_OVERLAY,
        ],
        metadata=meta,
    )
    return directive
