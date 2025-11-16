#!/usr/bin/env python3
"""
Monitor for incoming messages from another LLM environment.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent
MESSAGES_DIR = REPO_ROOT / ".idlergear" / "messages"
CLI_PREFIX = [sys.executable, "src/main.py"]


def run_idlergear_command(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """Run an idlergear CLI command relative to the repo root."""
    return subprocess.run(
        [*CLI_PREFIX, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def get_message_details(message_id: str) -> str:
    """Return formatted message details using the CLI formatter."""
    result = run_idlergear_command(["message", "read", "--id", message_id])
    return result.stdout.strip()


def get_unread_messages(from_source: str) -> List[dict]:
    """Load unread message JSON blobs for a given sender."""
    unread: List[dict] = []

    if not MESSAGES_DIR.exists():
        return unread

    for msg_file in sorted(MESSAGES_DIR.glob("*.json")):
        try:
            with msg_file.open("r") as handle:
                message = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        if message.get("from") != from_source:
            continue
        if message.get("status") == "read":
            continue
        unread.append(message)

    return unread


def monitor(from_source: str, interval: int, duration: int) -> None:
    """Poll the message directory for new messages."""
    print(f"🔍 Monitoring for messages from {from_source}...")
    print(f"   Checking every {interval} seconds for {duration // 60} minutes")
    print("   Press Ctrl+C to stop\n")

    seen_ids = {message["id"] for message in get_unread_messages(from_source)}
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(f"\n⏱️  Monitoring period ({duration // 60} minutes) completed")
                break

            messages = get_unread_messages(from_source)
            new_messages = [msg for msg in messages if msg["id"] not in seen_ids]

            if new_messages:
                for message in new_messages:
                    seen_ids.add(message["id"])
                    print("\n" + "=" * 70)
                    print("📨 NEW MESSAGE RECEIVED!")
                    print("=" * 70)
                    print(get_message_details(message["id"]))
                    print("=" * 70 + "\n")
            else:
                remaining = int(duration - elapsed)
                print(
                    f"\r⏳ Waiting for response... ({remaining}s remaining)",
                    end="",
                    flush=True,
                )

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Monitoring stopped by user")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor .idlergear/messages for new entries from a sender."
    )
    parser.add_argument(
        "--from-source",
        default="codex-local",
        help="Message source/user to watch (default: codex-local)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Total monitoring duration in seconds (default: 300 / 5 minutes)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = parse_args()
    monitor(arguments.from_source, arguments.interval, arguments.duration)
