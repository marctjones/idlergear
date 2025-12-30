"""IdlerGear Daemon - Multi-agent coordination via Unix socket."""

from idlergear.daemon.client import DaemonClient, DaemonError, DaemonNotRunning
from idlergear.daemon.lifecycle import DaemonLifecycle, ensure_daemon
from idlergear.daemon.protocol import Notification, Request, Response
from idlergear.daemon.server import DaemonServer

__all__ = [
    "DaemonClient",
    "DaemonError",
    "DaemonLifecycle",
    "DaemonNotRunning",
    "DaemonServer",
    "Notification",
    "Request",
    "Response",
    "ensure_daemon",
]
