#!/usr/bin/env python3
"""
Send a message and automatically monitor for responses
"""
import subprocess
import sys
import time
import json
from pathlib import Path

def send_message(to, body, from_name="claude-web"):
    """Send a message using idlergear"""
    print(f"📤 Sending message to {to}...")

    result = subprocess.run(
        [
            "python", "src/main.py", "message", "send",
            "--to", to,
            "--body", body,
            "--from", from_name
        ],
        capture_output=True,
        text=True,
        cwd="/home/user/idlergear"
    )

    if result.returncode != 0:
        print(f"❌ Error sending message: {result.stderr}")
        return None

    # Extract message ID from output
    # Format: "✅ Message <id> sent"
    output = result.stdout.strip()
    print(output)

    if "Message" in output and "sent" in output:
        message_id = output.split()[2]
        return message_id

    return None

def commit_message(message_id):
    """Commit the message to git"""
    print("\n📝 Committing message to git...")

    # Add the message file
    subprocess.run(
        ["git", "add", f".idlergear/messages/{message_id}.json"],
        cwd="/home/user/idlergear"
    )

    # Create commit
    commit_msg = f"feat: Send message {message_id} via idlergear"
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True,
        text=True,
        cwd="/home/user/idlergear"
    )

    if result.returncode == 0:
        print("✅ Message committed")
        return True
    else:
        print(f"⚠️  Commit failed: {result.stderr}")
        return False

def get_unread_messages(from_source):
    """Get all unread messages from a specific source"""
    messages_dir = Path("/home/user/idlergear/.idlergear/messages")
    unread = []

    if not messages_dir.exists():
        return unread

    for msg_file in messages_dir.glob("*.json"):
        try:
            with open(msg_file, 'r') as f:
                msg = json.load(f)
                if msg.get("from") == from_source and msg.get("status") != "read":
                    unread.append(msg)
        except Exception:
            continue

    return sorted(unread, key=lambda x: x.get("timestamp", ""))

def get_message_details(message_id):
    """Get full details of a specific message"""
    result = subprocess.run(
        ["python", "src/main.py", "message", "read", "--id", message_id],
        capture_output=True,
        text=True,
        cwd="/home/user/idlergear"
    )
    return result.stdout

def monitor_for_response(from_source, interval=5, duration=300):
    """Monitor for responses from a specific source"""
    print(f"\n🔍 Monitoring for responses from {from_source}...")
    print(f"   Checking every {interval} seconds for up to {duration//60} minutes")
    print(f"   Press Ctrl+C to stop early\n")

    seen_ids = set()
    start_time = time.time()

    # Mark existing messages as seen
    initial_messages = get_unread_messages(from_source)
    for msg in initial_messages:
        seen_ids.add(msg["id"])

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(f"\n⏱️  Monitoring period ({duration//60} minutes) completed with no response")
                break

            # Check for new messages
            messages = get_unread_messages(from_source)
            new_messages = [msg for msg in messages if msg["id"] not in seen_ids]

            if new_messages:
                for msg in new_messages:
                    print("\n" + "="*70)
                    print(f"📨 NEW RESPONSE RECEIVED!")
                    print("="*70)
                    print(get_message_details(msg["id"]))
                    print("="*70 + "\n")
                    seen_ids.add(msg["id"])

                print("✅ Response received - monitoring complete")
                return True
            else:
                remaining = int(duration - elapsed)
                print(f"\r⏳ Waiting for response... ({remaining}s remaining)    ", end="", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Monitoring stopped by user")
        return False

    return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python send_and_monitor.py <to> <message> [monitor_duration]")
        print("\nExample:")
        print('  python send_and_monitor.py codex-local "Hello, can you help with testing?" 180')
        sys.exit(1)

    to = sys.argv[1]
    body = sys.argv[2]
    monitor_duration = int(sys.argv[3]) if len(sys.argv) > 3 else 300

    # Send the message
    message_id = send_message(to, body)

    if not message_id:
        print("❌ Failed to send message")
        sys.exit(1)

    # Commit the message
    commit_message(message_id)

    # Monitor for response
    monitor_for_response(to, interval=5, duration=monitor_duration)

if __name__ == "__main__":
    main()
