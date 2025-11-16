"""
Log coordinator: Capture and manage logs from running processes.

Captures stdout/stderr from shell scripts and processes, stores them,
and makes them available for LLM analysis and debugging.
"""
import os
import subprocess
import time
import signal
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import threading


class LogCoordinator:
    """Coordinate log collection from running processes."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.logs_dir = self.project_path / ".idlergear" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.logs_dir / "metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load log session metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'sessions': {},
                'last_session_id': 0
            }
            # Save initial metadata
            self._save_initial_metadata()
    
    def _save_initial_metadata(self):
        """Save initial metadata file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _save_metadata(self):
        """Save log session metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _next_session_id(self) -> int:
        """Get next session ID."""
        self.metadata['last_session_id'] += 1
        return self.metadata['last_session_id']
    
    def attach_to_process(self, pid: int, name: Optional[str] = None) -> Dict:
        """
        Attach to an existing process and capture its output.
        Uses strace on Linux to capture stdout/stderr.
        """
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()
        
        if name is None:
            # Try to get process name
            try:
                result = subprocess.run(
                    ['ps', '-p', str(pid), '-o', 'comm='],
                    capture_output=True,
                    text=True,
                    check=True
                )
                name = result.stdout.strip()
            except:
                name = f"process-{pid}"
        
        log_file = self.logs_dir / f"session-{session_id}-{name}.log"
        
        session_info = {
            'session_id': session_id,
            'pid': pid,
            'name': name,
            'log_file': str(log_file),
            'started': timestamp,
            'status': 'capturing'
        }
        
        self.metadata['sessions'][str(session_id)] = session_info
        self._save_metadata()
        
        return session_info
    
    def capture_stdin(self, name: Optional[str] = None, source: Optional[str] = None) -> Dict:
        """
        Capture input from stdin (piped data).
        Useful for: ./run.sh | idlergear logs pipe --name my-app
        
        Args:
            name: Session name
            source: Optional description of source (e.g., "run.sh")
        
        Returns:
            Session info dict
        """
        import sys
        
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()
        
        if name is None:
            name = "piped-input"
        
        log_file = self.logs_dir / f"session-{session_id}-{name}.log"
        
        session_info = {
            'session_id': session_id,
            'source': source or 'stdin',
            'name': name,
            'log_file': str(log_file),
            'started': timestamp,
            'status': 'capturing',
            'cwd': str(self.project_path)
        }
        
        self.metadata['sessions'][str(session_id)] = session_info
        self._save_metadata()
        
        # Read from stdin and write to log file
        line_count = 0
        with open(log_file, 'w') as f:
            # Write header
            f.write(f"# Log Session {session_id}\n")
            f.write(f"# Source: {session_info['source']}\n")
            f.write(f"# Started: {timestamp}\n")
            f.write(f"# CWD: {session_info['cwd']}\n")
            f.write("#" + "=" * 70 + "\n\n")
            f.flush()
            
            # Read from stdin
            try:
                for line in sys.stdin:
                    f.write(line)
                    f.flush()
                    line_count += 1
                
                # Completed successfully
                session_info['status'] = 'completed'
                session_info['line_count'] = line_count
                
            except KeyboardInterrupt:
                # User interrupted
                session_info['status'] = 'stopped'
                session_info['line_count'] = line_count
                
            except Exception as e:
                session_info['status'] = 'failed'
                session_info['error'] = str(e)
                session_info['line_count'] = line_count
            
            finally:
                session_info['ended'] = datetime.now().isoformat()
                self._save_metadata()
                
                # Write footer
                f.write(f"\n#" + "=" * 70 + "\n")
                f.write(f"# Ended: {session_info['ended']}\n")
                f.write(f"# Lines captured: {line_count}\n")
        
        return session_info
    
    def run_with_capture(self, command: List[str], name: Optional[str] = None, 
                        cwd: Optional[str] = None) -> Dict:
        """
        Run a command and capture all its output.
        Returns session info.
        """
        session_id = self._next_session_id()
        timestamp = datetime.now().isoformat()
        
        if name is None:
            name = command[0]
        
        log_file = self.logs_dir / f"session-{session_id}-{name}.log"
        
        session_info = {
            'session_id': session_id,
            'command': ' '.join(command),
            'name': name,
            'log_file': str(log_file),
            'started': timestamp,
            'status': 'running',
            'cwd': cwd or str(self.project_path)
        }
        
        self.metadata['sessions'][str(session_id)] = session_info
        self._save_metadata()
        
        # Start process in background thread
        def run_process():
            try:
                with open(log_file, 'w') as f:
                    # Write header
                    f.write(f"# Log Session {session_id}\n")
                    f.write(f"# Command: {' '.join(command)}\n")
                    f.write(f"# Started: {timestamp}\n")
                    f.write(f"# CWD: {session_info['cwd']}\n")
                    f.write("#" + "=" * 70 + "\n\n")
                    f.flush()
                    
                    # Run command and capture output
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        cwd=cwd or self.project_path
                    )
                    
                    # Store PID
                    session_info['pid'] = process.pid
                    self._save_metadata()
                    
                    # Stream output to log file
                    for line in process.stdout:
                        f.write(line)
                        f.flush()
                    
                    process.wait()
                    
                    # Update session status
                    session_info['status'] = 'completed'
                    session_info['exit_code'] = process.returncode
                    session_info['ended'] = datetime.now().isoformat()
                    self._save_metadata()
                    
                    # Write footer
                    f.write(f"\n#" + "=" * 70 + "\n")
                    f.write(f"# Ended: {session_info['ended']}\n")
                    f.write(f"# Exit code: {process.returncode}\n")
                    
            except Exception as e:
                session_info['status'] = 'failed'
                session_info['error'] = str(e)
                session_info['ended'] = datetime.now().isoformat()
                self._save_metadata()
        
        thread = threading.Thread(target=run_process, daemon=True)
        thread.start()
        
        # Give it a moment to start
        time.sleep(0.1)
        
        return session_info
    
    def list_sessions(self) -> List[Dict]:
        """List all log sessions."""
        return list(self.metadata['sessions'].values())
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get session info by ID."""
        return self.metadata['sessions'].get(str(session_id))
    
    def read_log(self, session_id: int, tail: Optional[int] = None) -> str:
        """
        Read log for a session.
        If tail is specified, return last N lines.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        log_file = Path(session['log_file'])
        if not log_file.exists():
            return ""
        
        if tail:
            # Read last N lines
            try:
                result = subprocess.run(
                    ['tail', '-n', str(tail), str(log_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout
            except:
                # Fallback to reading full file
                pass
        
        return log_file.read_text()
    
    def stop_session(self, session_id: int) -> Dict:
        """Stop a running session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session['status'] != 'running':
            return session
        
        pid = session.get('pid')
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                session['status'] = 'stopped'
                session['ended'] = datetime.now().isoformat()
                self._save_metadata()
            except ProcessLookupError:
                session['status'] = 'completed'
                session['ended'] = datetime.now().isoformat()
                self._save_metadata()
        
        return session
    
    def cleanup_old_logs(self, days: int = 7) -> int:
        """Delete log files older than N days. Returns count deleted."""
        cutoff = time.time() - (days * 86400)
        deleted = 0
        
        sessions_to_remove = []
        for session_id, session in self.metadata['sessions'].items():
            log_file = Path(session['log_file'])
            if log_file.exists():
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    sessions_to_remove.append(session_id)
                    deleted += 1
        
        for session_id in sessions_to_remove:
            del self.metadata['sessions'][session_id]
        
        if sessions_to_remove:
            self._save_metadata()
        
        return deleted
    
    def export_session(self, session_id: int, output_file: str) -> str:
        """Export a session log to a file."""
        log_content = self.read_log(session_id)
        session = self.get_session(session_id)
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            f.write(f"# IdlerGear Log Export\n")
            f.write(f"# Session: {session_id}\n")
            f.write(f"# Name: {session.get('name', 'unknown')}\n")
            f.write(f"# Command: {session.get('command', 'N/A')}\n")
            f.write(f"# Started: {session.get('started', 'unknown')}\n")
            f.write(f"#" + "=" * 70 + "\n\n")
            f.write(log_content)
        
        return str(output_path)
