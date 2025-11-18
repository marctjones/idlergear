"""
eddi message server management for IdlerGear.

Handles installation, configuration, and operation of eddi-msgsrv
for secure Tor-based message passing between LLM environments.

Installation location: ~/.idlergear/bin/eddi-msgsrv
This keeps binaries and Tor secrets out of project repositories.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional


class EddiManager:
    """Manage eddi-msgsrv installation and operations."""

    EDDI_REPO = "https://github.com/marctjones/eddi"
    EDDI_BRANCH = "claude/cli-message-passing-01Sbqwn269RoUr7uc7yp4ce9"

    def __init__(self):
        # Install to user's home directory, NOT in any project repo
        self.idlergear_home = Path.home() / ".idlergear"
        self.bin_dir = self.idlergear_home / "bin"
        self.src_dir = self.idlergear_home / "src" / "eddi"
        self.binary_path = self.bin_dir / "eddi-msgsrv"

    def is_installed(self) -> bool:
        """Check if eddi-msgsrv is installed."""
        return self.binary_path.exists()

    def get_version(self) -> Optional[str]:
        """Get installed eddi version."""
        if not self.is_installed():
            return None

        try:
            result = subprocess.run(
                [str(self.binary_path), "--version"],
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
        Install eddi-msgsrv from source.

        Clones the eddi repo, builds with cargo, and installs
        the binary to ~/.idlergear/bin/

        Args:
            force: If True, reinstall even if already installed

        Returns:
            Dict with status, messages, and paths
        """
        result = {
            "status": "ok",
            "messages": [],
            "binary_path": str(self.binary_path),
        }

        # Check if already installed
        if self.is_installed() and not force:
            result["status"] = "already_installed"
            result["messages"].append(
                f"eddi-msgsrv already installed at {self.binary_path}"
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

            result["messages"].append(f"Installing eddi-msgsrv to {self.binary_path}")

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

            # Build with cargo
            result["messages"].append("Building with cargo (this may take a minute)...")

            # Find the msgsrv crate directory
            msgsrv_dir = self.src_dir / "crates" / "msgsrv"
            if not msgsrv_dir.exists():
                # Try root directory
                msgsrv_dir = self.src_dir

            build_result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd=msgsrv_dir,
                capture_output=True,
                text=True,
            )

            if build_result.returncode != 0:
                result["status"] = "error"
                result["error"] = f"Build failed: {build_result.stderr}"
                return result

            # Find and copy binary
            # Try common locations
            binary_locations = [
                msgsrv_dir / "target" / "release" / "eddi-msgsrv",
                self.src_dir / "target" / "release" / "eddi-msgsrv",
                msgsrv_dir / "target" / "release" / "msgsrv",
                self.src_dir / "target" / "release" / "msgsrv",
            ]

            binary_found = None
            for loc in binary_locations:
                if loc.exists():
                    binary_found = loc
                    break

            if not binary_found:
                result["status"] = "error"
                result["error"] = "Binary not found after build. Check cargo output."
                return result

            # Copy to bin directory
            shutil.copy2(binary_found, self.binary_path)
            os.chmod(self.binary_path, 0o755)

            result["messages"].append(f"Installed to {self.binary_path}")
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
        Uninstall eddi-msgsrv.

        Removes binary and optionally source code.

        Returns:
            Dict with status and messages
        """
        result = {
            "status": "ok",
            "messages": [],
        }

        if self.binary_path.exists():
            self.binary_path.unlink()
            result["messages"].append(f"Removed {self.binary_path}")
        else:
            result["messages"].append("Binary not found")

        # Note: We don't remove source by default to speed up reinstalls

        return result

    def status(self) -> Dict:
        """
        Get eddi installation status.

        Returns:
            Dict with installation info
        """
        return {
            "installed": self.is_installed(),
            "version": self.get_version(),
            "binary_path": str(self.binary_path) if self.is_installed() else None,
            "src_dir": str(self.src_dir) if self.src_dir.exists() else None,
        }
