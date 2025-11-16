#!/usr/bin/env python3
"""
Send a message via idlergear and optionally monitor for responses.
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
    return subprocess.run(
        [*CLI_PREFIX, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def send_message(to: str, body: str, from_name: str) -> Optional[str]:
    """Invoke the Typer command to send a message."""
    print(f"📤 Sending message to {to}...")
    result = run_idlergear_command(
        ["message", "send", "--to", to, "--body", body, "--from", from_name]
    )

    if result.returncode != 0:
        print(f"❌ Error sending message:\n{result.stderr.strip()}")
        return None

    output = result.stdout.strip()
    print(output)

    tokens = output.split()
    if len(tokens) >= 3 and tokens[0].startswith("✅") and tokens[1] == "Message":
        return tokens[2]

    return None


def commit_message(message_id: str, commit: bool) -> bool:
    """Stage and commit the new message JSON (if requested)."""
    if not commit:
        return True

    message_path = MESSAGES_DIR / f"{message_id}.json"
    if not message_path.exists():
        print(f"⚠️  Expected message file {message_path} not found.")
        return False

    print("\n📝 Committing message to git...")
    subprocess.run(["git", "add", str(message_path)], cwd=REPO_ROOT, check=False)
    commit_msg = f"feat: Send message {message_id} via idlergear"
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    if result.returncode == 0:
        print("✅ Message committed")
        return True

    print(f"⚠️  Commit failed:\n{result.stderr.strip()}")
    return False


def get_unread_messages(from_source: str) -> List[dict]:
    """Load unread message JSON blobs for a sender."""
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


def get_message_details(message_id: str) -> str:
    result = run_idlergear_command(["message", "read", "--id", message_id])
    return result.stdout.strip()


def monitor_for_response(
    from_source: str, interval: int, duration: int
) -> Optional[str]:
    """Poll for responses and return the first message ID if found."""
    print(f"\n🔍 Monitoring for responses from {from_source}...")
    print(f"   Checking every {interval} seconds for {duration // 60} minutes")
    print("   Press Ctrl+C to stop early\n")

    seen_ids = {message["id"] for message in get_unread_messages(from_source)}
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(
                    f"\n⏱️  Monitoring period ({duration // 60} minutes) completed with no response"
                )
                return None

            unread_messages = get_unread_messages(from_source)
            new_messages = [msg for msg in unread_messages if msg["id"] not in seen_ids]

            if new_messages:
                message = new_messages[0]
                seen_ids.add(message["id"])
                print("\n" + "=" * 70)
                print("📨 NEW RESPONSE RECEIVED!")
                print("=" * 70)
                print(get_message_details(message["id"]))
                print("=" * 70 + "\n")
                return message["id"]

            remaining = int(duration - elapsed)
            print(
                f"\r⏳ Waiting for response... ({remaining}s remaining)    ",
                end="",
                flush=True,
            )
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Monitoring stopped by user")
        return None


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send an idlergear message and optionally wait for a reply."
    )
    parser.add_argument("to", help="Recipient environment (e.g., codex-local)")
    parser.add_argument("body", help="Message body to send (quote for spaces)")
    parser.add_argument(
        "--from",
        dest="from_name",
        default="claude-web",
        help="Sender name recorded in the message (default: claude-web)",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor for a response after sending the message",
    )
    parser.add_argument(
        "--monitor-from",
        default=None,
        help="Override which sender to watch for responses (defaults to the recipient)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval when monitoring (default: 5 seconds)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Maximum monitoring duration in seconds (default: 300 / 5 minutes)",
    )
    parser.add_argument(
        "--skip-commit",
        action="store_true",
        help="Skip committing the generated message JSON",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    message_id = send_message(args.to, args.body, args.from_name)

    if not message_id:
        print("❌ Failed to send message")
        sys.exit(1)

    if not commit_message(message_id, commit=not args.skip_commit):
        print("⚠️  Message sent but not committed")

    if args.monitor:
        monitor_from = args.monitor_from or args.to
        monitor_for_response(monitor_from, args.interval, args.duration)


if __name__ == "__main__":
    main()
