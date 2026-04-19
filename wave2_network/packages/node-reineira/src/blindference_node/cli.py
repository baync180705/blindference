from __future__ import annotations

import argparse
import asyncio
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blindference-node", description="Run a Blindference protocol node.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize local node state.")
    init_parser.add_argument("--data-dir", default=str(Path.home() / ".blindference"))

    subparsers.add_parser("start", help="Start the demo worker.")
    subparsers.add_parser("status", help="Show runtime configuration.")

    attest_parser = subparsers.add_parser("attest", help="Print a placeholder attestation action.")
    attest_parser.add_argument("attestation_type")
    attest_parser.add_argument("--document", required=True)
    attest_parser.add_argument("--counterparty", default="0x0000000000000000000000000000000000000000")
    attest_parser.add_argument("--expires-at", type=int, default=0)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        data_dir = Path(args.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"Initialized node data directory at {data_dir}")
        print("Set BLINDFERENCE_NODE_* env vars, then run `blindference-node start`.")
        return

    if args.command == "status":
        from blindference_node.config import NodeSettings

        settings = NodeSettings()
        print(f"ICL: {settings.icl_base_url}")
        print(f"Provider: {settings.provider}")
        print(f"Mock mode: {settings.mock_cloud_inference}")
        return

    if args.command == "start":
        from blindference_node.config import NodeSettings
        from blindference_node.worker import BlindferenceDemoWorker

        settings = NodeSettings()
        print(f"Connecting to ICL at {settings.icl_base_url}")
        print(
            f"Using provider={settings.provider} model="
            f"{settings.groq_model if settings.provider.lower() == 'groq' else settings.gemini_model}"
        )
        if settings.mock_cloud_inference:
            print("Mock cloud inference is enabled for local Anvil demos.")
        asyncio.run(BlindferenceDemoWorker(settings).run())
        return

    print(
        f"Would publish attestation type={args.attestation_type} doc={args.document} "
        f"counterparty={args.counterparty} expires_at={args.expires_at}"
    )
    print("Attestation publish remains a placeholder in this demo worker.")


if __name__ == "__main__":
    main()
