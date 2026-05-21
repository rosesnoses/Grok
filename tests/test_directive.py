"""Placeholder tests for v1 public import.

In a real release these would validate round-tripping, deterministic seeds,
layer presence, and SVA6 extraction.
"""

from sangraha.aurion_art_directive import AurionArtDirectiveV1


def test_directive_model_roundtrip():
    d = AurionArtDirectiveV1.model_validate_json(
        open("examples/aurion-directive-v1.example.json").read()
    )
    assert d.version == "aurion-art-directive-v1"
    assert d.geometry.symmetry >= 3
    json_back = d.to_json()
    assert "lotus-throne" in json_back
