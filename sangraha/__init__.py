"""Sangraha public API — the reversible Aurion-powered mandala forge.

This package now ships the full production implementation from the psycho-mandala lineage:
- Aurion Art Directive v1 (ArtDirective + build_art_directive)
- Audio Gearing (acoustic features → geared cosmic matrix)
- Sangraha high-fidelity reversible SVA6 renderer + embedding
"""

from .aurion_art_directive import (
    ArtDirective,
    art_directive_from_json,
    art_directive_to_json,
    build_art_directive,
)
from .audio_gearing import build_geared_cosmic_matrix
from .sangraha import main as sangraha_main

__all__ = [
    "ArtDirective",
    "build_art_directive",
    "art_directive_to_json",
    "art_directive_from_json",
    "build_geared_cosmic_matrix",
    "sangraha_main",
]

__version__ = "0.1.0"

