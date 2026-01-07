#!/usr/bin/env python3
"""
WebSocket Test Client

This script demonstrates how to connect to the WebSocket endpoint
and receive real-time progress updates.

Usage:
    python test_websocket.py <jwt_token>
"""

import asyncio
import sys
import json
import websockets


async def test_websocket(token: str):
    """
    Connect to WebSocket and listen for progress updates.

    Args:
        token: JWT authentication token
    """
    uri = f"ws://localhost:8000/ws/progress?token={token}"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket!")

            # Listen for messages
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Pretty print the message
                    print(f"\n📨 Received: {data['type']}")
                    print(f"   {json.dumps(data, indent=2)}")

                    # Handle different message types
                    if data['type'] == 'connected':
                        print(f"   ✓ {data['message']}")

                    elif data['type'] == 'download_progress':
                        progress = data.get('progress', 0) * 100
                        print(f"   📥 Download: {progress:.1f}% complete")

                    elif data['type'] == 'export_progress':
                        progress = data.get('progress', 0) * 100
                        print(f"   🎬 Export: {progress:.1f}% complete")

                    elif data['type'] == 'task_complete':
                        print(f"   ✅ Task completed: {data.get('message')}")

                    elif data['type'] == 'error':
                        print(f"   ❌ Error: {data.get('message')}")

                    elif data['type'] == 'pong':
                        print("   🏓 Pong received")

                except websockets.exceptions.ConnectionClosed:
                    print("\n⚠️  Connection closed")
                    break
                except KeyboardInterrupt:
                    print("\n👋 Disconnecting...")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure you're using a valid JWT token")
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_websocket.py <jwt_token>")
        print("\nTo get a JWT token:")
        print("1. Login via API: POST http://localhost:8000/api/v1/auth/login")
        print("2. Copy the 'access_token' from the response")
        print("3. Run: python test_websocket.py YOUR_TOKEN_HERE")
        sys.exit(1)

    token = sys.argv[1]

    print("=" * 60)
    print("WebSocket Progress Test Client")
    print("=" * 60)
    print("\nThis will connect to the WebSocket and show real-time updates.")
    print("Start a download or video build in another terminal to see updates.")
    print("\nPress Ctrl+C to exit\n")

    try:
        asyncio.run(test_websocket(token))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
