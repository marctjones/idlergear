"""
eddi management for IdlerGear.

Handles installation, configuration, and operation of eddi tools:
- eddi-server: Serve apps as Tor hidden services
- eddi-msgsrv: Message server for LLM-to-LLM and generic messaging

Installation location: ~/.idlergear/bin/
This keeps binaries and Tor secrets out of project repositories.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List


class EddiManager:
    """Manage eddi installation and operations."""

    EDDI_REPO = "https://github.com/marctjones/eddi"
    EDDI_BRANCH = "claude/cli-message-passing-01Sbqwn269RoUr7uc7yp4ce9"

    def __init__(self):
        # Install to user's home directory, NOT in any project repo
        self.idlergear_home = Path.home() / ".idlergear"
        self.bin_dir = self.idlergear_home / "bin"
        self.src_dir = self.idlergear_home / "src" / "eddi"
        # Primary binaries
        self.server_path = self.bin_dir / "eddi-server"
        self.msgsrv_path = self.bin_dir / "eddi-msgsrv"
        # Legacy compatibility
        self.binary_path = self.server_path

    def is_installed(self) -> bool:
        """Check if eddi binaries are installed."""
        return self.server_path.exists() or self.msgsrv_path.exists()

    def get_version(self) -> Optional[str]:
        """Get installed eddi version."""
        if not self.is_installed():
            return None

        # Try eddi-server first, then eddi-msgsrv
        for binary in [self.server_path, self.msgsrv_path]:
            if binary.exists():
                try:
                    result = subprocess.run(
                        [str(binary), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()
                except Exception:
                    pass

        return "unknown"

    def install(self, force: bool = False) -> Dict:
        """
        Install eddi binaries from source.

        Clones the eddi repo, builds with cargo, and installs
        eddi-server and eddi-msgsrv to ~/.idlergear/bin/

        Args:
            force: If True, reinstall even if already installed

        Returns:
            Dict with status, messages, and paths
        """
        result = {
            "status": "ok",
            "messages": [],
            "binaries": {
                "eddi-server": str(self.server_path),
                "eddi-msgsrv": str(self.msgsrv_path),
            },
        }

        # Check if already installed
        if self.is_installed() and not force:
            result["status"] = "already_installed"
            result["messages"].append(
                f"eddi already installed at {self.bin_dir}"
            )
            result["messages"].append("Use --force to reinstall")
            return result

        # Check for cargo (Rust build tool)
        if not shutil.which("cargo"):
            result["status"] = "error"
            result["error"] = "cargo not found. Please install Rust: https://rustup.rs"
            return result

        # Check for git
        if not shutil.which("git"):
            result["status"] = "error"
            result["error"] = "git not found. Please install git."
            return result

        try:
            # Create directories
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            self.src_dir.parent.mkdir(parents=True, exist_ok=True)

            result["messages"].append(f"Installing eddi to {self.bin_dir}")

            # Clone or update repo
            if self.src_dir.exists():
                result["messages"].append("Updating existing source...")
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=self.src_dir,
                    capture_output=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "checkout", self.EDDI_BRANCH],
                    cwd=self.src_dir,
                    capture_output=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "pull", "origin", self.EDDI_BRANCH],
                    cwd=self.src_dir,
                    capture_output=True,
                    check=True,
                )
            else:
                result["messages"].append(f"Cloning {self.EDDI_REPO}...")
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        self.EDDI_BRANCH,
                        self.EDDI_REPO,
                        str(self.src_dir),
                    ],
                    capture_output=True,
                    check=True,
                )

            # Build with cargo from root directory
            result["messages"].append("Building with cargo (this may take a minute)...")

            build_result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd=self.src_dir,
                capture_output=True,
                text=True,
            )

            if build_result.returncode != 0:
                result["status"] = "error"
                result["error"] = f"Build failed: {build_result.stderr}"
                return result

            # Find and copy binaries
            target_dir = self.src_dir / "target" / "release"
            binaries_to_install = [
                ("eddi-server", self.server_path),
                ("eddi-msgsrv", self.msgsrv_path),
            ]

            installed_count = 0
            for binary_name, dest_path in binaries_to_install:
                src_binary = target_dir / binary_name
                if src_binary.exists():
                    shutil.copy2(src_binary, dest_path)
                    os.chmod(dest_path, 0o755)
                    result["messages"].append(f"Installed {binary_name} to {dest_path}")
                    installed_count += 1

            if installed_count == 0:
                result["status"] = "error"
                result["error"] = "No binaries found after build. Check cargo output."
                return result

            result["messages"].append("")
            result["messages"].append("Add to PATH (optional):")
            result["messages"].append(f'  export PATH="{self.bin_dir}:$PATH"')

        except subprocess.CalledProcessError as e:
            result["status"] = "error"
            result["error"] = f"Command failed: {e}"
            if hasattr(e, "stderr") and e.stderr:
                result["error"] += f"\n{e.stderr}"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def uninstall(self) -> Dict:
        """
        Uninstall eddi binaries.

        Removes eddi-server and eddi-msgsrv binaries.

        Returns:
            Dict with status and messages
        """
        result = {
            "status": "ok",
            "messages": [],
        }

        removed_count = 0
        for binary_path in [self.server_path, self.msgsrv_path]:
            if binary_path.exists():
                binary_path.unlink()
                result["messages"].append(f"Removed {binary_path}")
                removed_count += 1

        if removed_count == 0:
            result["messages"].append("No binaries found")

        # Note: We don't remove source by default to speed up reinstalls

        return result

    def status(self) -> Dict:
        """
        Get eddi installation status.

        Returns:
            Dict with installation info
        """
        binaries = {}
        if self.server_path.exists():
            binaries["eddi-server"] = str(self.server_path)
        if self.msgsrv_path.exists():
            binaries["eddi-msgsrv"] = str(self.msgsrv_path)

        return {
            "installed": self.is_installed(),
            "version": self.get_version(),
            "binary_path": str(self.server_path) if self.server_path.exists() else str(self.msgsrv_path) if self.msgsrv_path.exists() else None,
            "binaries": binaries,
            "src_dir": str(self.src_dir) if self.src_dir.exists() else None,
        }
