from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(
    name="blindference-node",
    help="Run a Blindference protocol node.",
    no_args_is_help=True,
)


@app.command()
def init(
    data_dir: Path = typer.Option(
        Path.home() / ".blindference",
        "--data-dir",
        help="Where to store node state, keys, and config.",
    ),
) -> None:
    """Initialize a fresh node identity, key, and default config."""
    data_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Initialized node data directory at {data_dir}")
    typer.echo("Next: edit config.yaml, then run `blindference-node start`.")


@app.command()
def start(
    config: Path = typer.Option(
        Path.home() / ".blindference" / "config.yaml",
        "--config",
        help="Path to node config file.",
    ),
) -> None:
    """Start the node — Sprint participation, attestation listener, inference executor."""
    typer.echo(f"Loading config from {config}")
    typer.echo("Node startup not implemented yet (placeholder).")


@app.command()
def status() -> None:
    """Print node identity, registered attestations, current reputation, pending rewards."""
    typer.echo("Status not implemented yet (placeholder).")


@app.command()
def attest(
    attestation_type: str = typer.Argument(..., help="e.g., zdr.v1, hipaa-baa.v1"),
    document: Path = typer.Option(..., "--document", help="Off-chain document being committed to."),
    counterparty: str = typer.Option(
        "0x0000000000000000000000000000000000000000",
        "--counterparty",
        help="Address of the counterparty (0x0 = public commitment).",
    ),
    expires_at: int = typer.Option(0, "--expires-at", help="Unix epoch; 0 = no expiry."),
) -> None:
    """Publish a signed attestation to NodeAttestationRegistry."""
    typer.echo(
        f"Would publish attestation type={attestation_type} doc={document} "
        f"counterparty={counterparty} expires_at={expires_at}"
    )
    typer.echo("Attestation publish not implemented yet (placeholder).")


if __name__ == "__main__":
    app()
