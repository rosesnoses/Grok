"""Sangraha CLI — forge, inspect, and extract SVA6 artifacts from the command line."""

from __future__ import annotations

import json
from pathlib import Path

import click

from .aurion_art_directive import AurionArtDirectiveV1
from .sangraha import extract_audio_from_sva6, forge, render_from_directive


@click.group()
def cli() -> None:
    """🌀 Sangraha — reversible high-fidelity mandala forger (Aurion Directive + SVA6)."""
    pass


@cli.command()
@click.argument("audio_or_directive", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--directive", "-d", type=click.Path(exists=True, path_type=Path), help="Path to aurion-art-directive-v1 JSON")
@click.option("--size", "-s", default=4096, show_default=True, help="Output pixel width/height")
@click.option("--supersample", default=2, show_default=True, help="Internal supersampling factor")
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Output PNG path")
@click.option("--title", help="Optional song title for metadata")
@click.option("--artist", help="Optional artist for metadata")
def forge_cmd(audio_or_directive: Path | None, directive: Path | None, size: int, supersample: int, output: Path | None, title: str | None, artist: str | None) -> None:
    """Forge a reversible SVA6 PNG from audio or a pre-generated directive."""
    if audio_or_directive and audio_or_directive.suffix.lower() == ".json":
        # treat as directive
        directive = audio_or_directive
        audio_or_directive = None

    if directive:
        dir_obj = AurionArtDirectiveV1.model_validate_json(directive.read_text())
        out = forge(directive=dir_obj, size=size, supersample=supersample, output=output)
    elif audio_or_directive:
        out = forge(audio_or_directive, size=size, supersample=supersample, output=output)
    else:
        raise click.UsageError("Provide an audio file or --directive JSON")

    click.echo(f"✨ Forged {out}")


@cli.command()
@click.argument("sva6_png", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), required=True, help="Where to write the recovered audio")
def extract_audio(sva6_png: Path, output: Path) -> None:
    """Extract the original audio payload from an SVA6 artifact (round-trip verification)."""
    audio = extract_audio_from_sva6(sva6_png)
    output.write_bytes(audio)
    click.echo(f"🔓 Recovered {len(audio)} bytes → {output}")


@cli.command()
@click.argument("directive_json", type=click.Path(exists=True, path_type=Path))
@click.option("--size", default=1024, show_default=True)
def preview(directive_json: Path, size: int) -> None:
    """Quickly render a preview PNG from a directive JSON (no audio embedding)."""
    directive = AurionArtDirectiveV1.model_validate_json(directive_json.read_text())
    png = render_from_directive(directive, size=size)
    out = directive_json.with_suffix(".preview.png")
    out.write_bytes(png)
    click.echo(f"🖼️  Preview saved to {out}")


@cli.command()
def version() -> None:
    """Print Sangraha + directive version info."""
    click.echo("Sangraha v0.1.0 — aurion-art-directive-v1")
    click.echo("SVA6 reversible contract (transitional v1 trailer)")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
