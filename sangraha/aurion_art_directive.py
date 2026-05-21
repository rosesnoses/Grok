"""Aurion Art Directive v1 — the canonical contract between audio, browser preview, and Sangraha.

This module defines the single source of truth JSON schema (Pydantic model) that guarantees
visual-family parity between the live browser lab and the high-fidelity reversible Sangraha renderer.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DirectiveVersion(str, Enum):
    V1 = "aurion-art-directive-v1"


class SourceAudio(BaseModel):
    sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$", description="SHA-256 of the canonical source audio bytes")
    duration_s: float = Field(..., gt=0, description="Duration in seconds")
    bpm: float | None = Field(None, ge=20, le=300)
    spectral_centroid: float | None = Field(None, ge=0)
    rms_energy: float | None = Field(None, ge=0, le=1)
    zero_crossing_rate: float | None = Field(None, ge=0)


class Archetype(BaseModel):
    id: str = Field(..., min_length=3, description="Stable identifier, e.g. 'lotus-throne-13'")
    family: str = Field(..., description="High-level visual family: floral-cosmic, fractal-storm, etc.")
    name: str = Field(..., description="Human-friendly display name")


class Geometry(BaseModel):
    symmetry: int = Field(6, ge=3, le=24, description="Rotational symmetry order (petals / axes)")
    rings: int = Field(9, ge=1, le=36, description="Number of concentric structural rings")
    petal_density: float = Field(1.0, ge=0.1, le=8.0)
    spiral_tension: float = Field(0.7, ge=0.0, le=1.5, description="How tightly spirals wind")
    energy_bias: float = Field(0.5, ge=0.0, le=1.0, description="0 = calm/outer, 1 = explosive/center-weighted")


class ColorSpec(BaseModel):
    palette: str = Field("plasma-dawn", description="Named palette family used by both renderers")
    primary_hue: int = Field(260, ge=0, le=360, description="Base hue in degrees for the dominant color")
    saturation: float = Field(0.85, ge=0.0, le=1.0)
    glow_temperature: int = Field(5800, ge=2000, le=12000, description="Kelvin for glow color temperature")


class LayerName(str, Enum):
    BASE_CYMATICS = "base_cymatic_field"
    SKELETON = "mandala_skeleton"
    FILAMENTS = "filament_network"
    GLOW_VEINS = "glow_veins"
    STAR_NODES = "star_nodes"
    ENERGY_OVERLAY = "logo_energy_overlay"
    # Future layers for v2+
    ORBIT_TRAPS = "orbit_trap_filigree"
    DEEP_SPACE = "deep_space_dust"


class RenderTarget(str, Enum):
    PREVIEW = "preview"
    PRINT = "print-300dpi"
    MASTER_8K = "8k-master"


class AurionArtDirectiveV1(BaseModel):
    """The v1 directive — everything the browser and Sangraha need to speak the same visual language."""

    version: Literal["aurion-art-directive-v1"] = DirectiveVersion.V1.value
    source_audio: SourceAudio
    seed: int = Field(..., description="Deterministic 32-bit seed derived from audio content + user salt")
    archetype: Archetype
    geometry: Geometry = Field(default_factory=Geometry)
    color: ColorSpec = Field(default_factory=ColorSpec)
    layers: list[LayerName] = Field(
        default_factory=lambda: [
            LayerName.BASE_CYMATICS,
            LayerName.SKELETON,
            LayerName.FILAMENTS,
            LayerName.GLOW_VEINS,
            LayerName.STAR_NODES,
            LayerName.ENERGY_OVERLAY,
        ]
    )
    render_targets: list[RenderTarget] = Field(
        default_factory=lambda: [RenderTarget.PREVIEW, RenderTarget.MASTER_8K]
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form provenance, song title, artist, etc."
    )

    @field_validator("layers")
    @classmethod
    def at_least_one_layer(cls, v: list[LayerName]) -> list[LayerName]:
        if not v:
            raise ValueError("At least one layer must be enabled")
        return v

    def to_json(self, **kwargs) -> str:
        return self.model_dump_json(indent=2, **kwargs)

    @classmethod
    def from_json(cls, data: str) -> AurionArtDirectiveV1:
        return cls.model_validate_json(data)


# Convenience type alias
Directive = AurionArtDirectiveV1
