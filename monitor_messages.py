#!/usr/bin/env python3
"""
Monitor for incoming messages from local LLM
"""
import subprocess
import json
import time
import sys
from pathlib import Path

def get_messages_from_source(source):
    """Get all messages from a specific source"""
    result = subprocess.run(
        ["python", "src/main.py", "message", "list", "--filter-from", source],
        capture_output=True,
        text=True,
        cwd="/home/user/idlergear"
    )
    return result.stdout

def get_message_details(message_id):
    """Get full details of a specific message"""
    result = subprocess.run(
        ["python", "src/main.py", "message", "read", "--id", message_id],
        capture_output=True,
        text=True,
        cwd="/home/user/idlergear"
    )
    return result.stdout

def get_unread_messages():
    """Get all unread messages from codex-local"""
    messages_dir = Path("/home/user/idlergear/.idlergear/messages")
    unread = []

    if not messages_dir.exists():
        return unread

    for msg_file in messages_dir.glob("*.json"):
        try:
            with open(msg_file, 'r') as f:
                msg = json.load(f)
                if msg.get("from") == "codex-local" and msg.get("status") != "read":
                    unread.append(msg)
        except Exception:
            continue

    return unread

def monitor(interval=5, duration=300):
    """
    Monitor for new messages

    Args:
        interval: Check interval in seconds (default: 5)
        duration: Total monitoring duration in seconds (default: 300 = 5 minutes)
    """
    print(f"🔍 Monitoring for messages from codex-local...")
    print(f"   Checking every {interval} seconds for {duration//60} minutes")
    print(f"   Press Ctrl+C to stop\n")

    seen_ids = set()
    start_time = time.time()

    # Get initial message IDs to mark as seen
    initial_messages = get_unread_messages()
    for msg in initial_messages:
        seen_ids.add(msg["id"])

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(f"\n⏱️  Monitoring period ({duration//60} minutes) completed")
                break

            # Check for new messages
            messages = get_unread_messages()
            new_messages = [msg for msg in messages if msg["id"] not in seen_ids]

            if new_messages:
                for msg in new_messages:
                    print("\n" + "="*70)
                    print(f"📨 NEW MESSAGE RECEIVED!")
                    print("="*70)
                    print(get_message_details(msg["id"]))
                    print("="*70 + "\n")
                    seen_ids.add(msg["id"])
            else:
                # Show waiting indicator
                remaining = int(duration - elapsed)
                print(f"\r⏳ Waiting for response... ({remaining}s remaining)", end="", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Monitoring stopped by user")
        return

if __name__ == "__main__":
    # Parse command line arguments
    interval = 5  # Check every 5 seconds
    duration = 300  # Monitor for 5 minutes by default

    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Invalid duration: {sys.argv[1]}")
            sys.exit(1)

    monitor(interval=interval, duration=duration)
