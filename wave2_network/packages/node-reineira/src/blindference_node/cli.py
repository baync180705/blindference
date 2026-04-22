from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import httpx
import uvicorn


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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
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
        from blindference_node.server import create_node_app
        from blindference_node.worker import BlindferenceDemoWorker

        settings = NodeSettings()
        if not settings.operator_private_key:
            raise RuntimeError("BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY must be set for event-driven runtime mode.")

        worker = BlindferenceDemoWorker(settings)
        callback_url = settings.callback_public_url or f"http://{settings.callback_host}:{settings.callback_port}"
        operator_address = worker.cofhe_bridge.operator_address if worker.cofhe_bridge else "unknown"

        print(f"Connecting to ICL at {settings.icl_base_url}")
        print(
            f"Using provider={settings.provider} model="
            f"{settings.groq_model if settings.provider.lower() == 'groq' else settings.gemini_model}"
        )
        print(f"Operator address={operator_address}")
        print(f"Callback URL={callback_url}")
        if settings.mock_cloud_inference:
            print("Mock cloud inference is enabled for local Anvil demos.")

        async def run_event_driven_runtime() -> None:
            app = create_node_app(worker)
            config = uvicorn.Config(
                app,
                host=settings.callback_host,
                port=settings.callback_port,
                log_level="warning",
            )
            server = uvicorn.Server(config)

            async def register_runtime() -> None:
                await asyncio.sleep(0.5)
                async with httpx.AsyncClient(base_url=settings.icl_base_url, timeout=10.0) as client:
                    while not server.should_exit:
                        try:
                            response = await client.post(
                                "/internal/operators/runtime",
                                json={
                                    "operator_address": operator_address,
                                    "callback_url": callback_url,
                                },
                            )
                            response.raise_for_status()
                            print(f"Registered node runtime: {response.json()}")
                        except Exception as error:
                            logging.getLogger("blindference.node").warning(
                                "Runtime registration heartbeat failed for operator=%s: %s",
                                operator_address,
                                error,
                            )
                        await asyncio.sleep(settings.runtime_registration_interval_seconds)

            server_task = asyncio.create_task(server.serve())
            worker_task = asyncio.create_task(worker.run())
            register_task = asyncio.create_task(register_runtime())
            try:
                await asyncio.gather(server_task, worker_task, register_task)
            finally:
                server.should_exit = True

        asyncio.run(run_event_driven_runtime())
        return

    print(
        f"Would publish attestation type={args.attestation_type} doc={args.document} "
        f"counterparty={args.counterparty} expires_at={args.expires_at}"
    )
    print("Attestation publish remains a placeholder in this demo worker.")


if __name__ == "__main__":
    main()
