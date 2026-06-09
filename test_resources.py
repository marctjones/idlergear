#!/usr/bin/env python3
"""Test script for MCP Resources implementation."""

import asyncio
from idlergear import mcp_resources


async def test_resources():
    """Test resource listing and reading."""
    print("=" * 60)
    print("Testing MCP Resources Implementation (Phase 0.1)")
    print("=" * 60)
    print()

    # Test listing resources
    print("1. Testing list_resources():")
    print("-" * 60)
    resources = mcp_resources.list_resources()
    print(f"Found {len(resources)} resources:")
    for r in resources:
        print(f"  - {r.uri}")
        print(f"    Name: {r.name}")
        print(f"    Type: {r.mimeType}")
        print()

    # Test reading specific resources
    print("\n2. Testing read_resource():")
    print("-" * 60)

    test_uris = [
        "idlergear://project/vision",
        "idlergear://project/context/minimal",
        "idlergear://project/tasks/summary",
        "idlergear://system/status",
        "idlergear://graph/stats",
    ]

    for uri in test_uris:
        print(f"\nReading: {uri}")
        try:
            content = mcp_resources.read_resource(uri)
            # Truncate long content
            if len(content) > 200:
                print(f"  Content ({len(content)} chars): {content[:200]}...")
            else:
                print(f"  Content: {content}")
        except Exception as e:
            print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_resources())
