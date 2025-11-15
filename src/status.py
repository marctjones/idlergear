"""
Status command: Show project health and state.
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


class ProjectStatus:
    """Collect and format project status information."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self._git_root = None
        self._is_git_repo = None
    
    @property
    def is_git_repo(self) -> bool:
        """Check if current directory is in a git repository."""
        if self._is_git_repo is None:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--git-dir"],
                    cwd=self.project_path,
                    capture_output=True,
                    check=True
                )
                self._is_git_repo = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._is_git_repo = False
        return self._is_git_repo
    
    @property
    def git_root(self) -> Optional[Path]:
        """Get git repository root."""
        if self._git_root is None and self.is_git_repo:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self._git_root = Path(result.stdout.strip())
            except subprocess.CalledProcessError:
                self._git_root = None
        return self._git_root
    
    def get_git_branch(self) -> Optional[str]:
        """Get current git branch name."""
        if not self.is_git_repo:
            return None
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def get_uncommitted_changes(self) -> int:
        """Count uncommitted changes."""
        if not self.is_git_repo:
            return 0
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            lines = [line for line in result.stdout.strip().split('\n') if line]
            return len(lines)
        except subprocess.CalledProcessError:
            return 0
    
    def get_all_branches(self) -> List[Dict[str, str]]:
        """Get all local and remote branches."""
        if not self.is_git_repo:
            return []
        try:
            result = subprocess.run(
                ["git", "branch", "-a", "--format=%(refname:short)|%(upstream:short)|%(committerdate:relative)"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            branches = []
            current_branch = self.get_git_branch()
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) >= 1:
                        branch_name = parts[0].strip()
                        # Skip remote tracking refs
                        if branch_name.startswith('remotes/'):
                            continue
                        
                        upstream = parts[1].strip() if len(parts) > 1 else ""
                        last_commit = parts[2].strip() if len(parts) > 2 else ""
                        
                        branches.append({
                            'name': branch_name,
                            'upstream': upstream,
                            'last_commit': last_commit,
                            'is_current': branch_name == current_branch
                        })
            return branches
        except subprocess.CalledProcessError:
            return []
    
    def get_recent_commits(self, count: int = 3) -> List[Dict[str, str]]:
        """Get recent commit history."""
        if not self.is_git_repo:
            return []
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%h|%s|%ar"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        commits.append({
                            'hash': parts[0],
                            'message': parts[1],
                            'time': parts[2]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def get_llm_managed_branches(self) -> Dict[str, List[str]]:
        """Identify branches managed by LLM tools."""
        branches = self.get_all_branches()
        
        llm_branches = {
            'web_sync': [],      # idlergear-web-sync branches
            'claude': [],        # claude-*, claude-code-*
            'copilot': [],       # copilot-*, github-copilot-*
            'gemini': [],        # gemini-*
            'other_llm': [],     # Other patterns
            'dangling': []       # Old branches with no recent activity
        }
        
        current_branch = self.get_git_branch()
        main_branches = ['main', 'master', 'develop']
        
        for branch in branches:
            name = branch['name']
            last_commit = branch['last_commit']
            
            # Skip main branches
            if name in main_branches or branch['is_current']:
                continue
            
            # Identify by naming pattern
            if 'idlergear' in name and 'sync' in name:
                llm_branches['web_sync'].append(name)
            elif name.startswith('claude') or 'claude-code' in name:
                llm_branches['claude'].append(name)
            elif name.startswith('copilot') or 'github-copilot' in name:
                llm_branches['copilot'].append(name)
            elif name.startswith('gemini'):
                llm_branches['gemini'].append(name)
            elif any(pattern in name.lower() for pattern in ['ai-', 'llm-', 'assistant-']):
                llm_branches['other_llm'].append(name)
            
            # Check for dangling branches (no activity in 7+ days)
            if last_commit and any(term in last_commit for term in ['week', 'month', 'year']):
                # Try to parse "2 weeks ago" format
                if 'week' in last_commit:
                    weeks = int(last_commit.split()[0]) if last_commit.split()[0].isdigit() else 1
                    if weeks >= 1:
                        llm_branches['dangling'].append(name)
                elif 'month' in last_commit or 'year' in last_commit:
                    llm_branches['dangling'].append(name)
        
        return llm_branches
        """Get recent commit history."""
        if not self.is_git_repo:
            return []
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%h|%s|%ar"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        commits.append({
                            'hash': parts[0],
                            'message': parts[1],
                            'time': parts[2]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def get_charter_doc_age(self, filename: str) -> Optional[str]:
        """Get age of a charter document (VISION.md, TODO.md, etc.)."""
        if not self.git_root:
            return None
        
        doc_path = self.git_root / filename
        if not doc_path.exists():
            return "Not found"
        
        try:
            # Get last modification time from git
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ar", "--", filename],
                cwd=self.git_root,
                capture_output=True,
                text=True,
                check=True
            )
            age = result.stdout.strip()
            return age if age else "Never committed"
        except subprocess.CalledProcessError:
            # Fall back to file system mtime
            mtime = doc_path.stat().st_mtime
            age_seconds = datetime.now().timestamp() - mtime
            age_days = int(age_seconds / 86400)
            
            if age_days == 0:
                return "Today"
            elif age_days == 1:
                return "1 day ago"
            elif age_days < 7:
                return f"{age_days} days ago"
            elif age_days < 30:
                weeks = age_days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                months = age_days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
    
    def get_project_name(self) -> str:
        """Get project name from directory or git repo."""
        if self.git_root:
            return self.git_root.name
        return self.project_path.name
    
    def format_status(self) -> str:
        """Format status information for display."""
        lines = []
        
        # Header
        lines.append("")
        lines.append(f"📊 Project: {self.get_project_name()}")
        lines.append(f"📍 Location: {self.project_path}")
        lines.append("")
        
        # Git status
        if self.is_git_repo:
            lines.append("🌿 Git Status:")
            branch = self.get_git_branch()
            if branch:
                lines.append(f"  Branch: {branch}")
            
            uncommitted = self.get_uncommitted_changes()
            if uncommitted > 0:
                lines.append(f"  Uncommitted changes: {uncommitted} file{'s' if uncommitted != 1 else ''}")
            else:
                lines.append("  Uncommitted changes: None ✅")
            
            commits = self.get_recent_commits()
            if commits:
                lines.append("  Recent commits:")
                for commit in commits:
                    lines.append(f"    - {commit['message']} ({commit['time']})")
            lines.append("")
        else:
            lines.append("⚠️  Not a git repository")
            lines.append("")
        
        # Charter documents
        lines.append("📋 Charter Documents:")
        charter_docs = ['VISION.md', 'TODO.md', 'IDEAS.md', 'DESIGN.md', 'DEVELOPMENT.md']
        
        for doc in charter_docs:
            age = self.get_charter_doc_age(doc)
            if age == "Not found":
                lines.append(f"  {doc}: Not found ⚠️")
            elif age == "Never committed":
                lines.append(f"  {doc}: Exists but never committed ⚠️")
            else:
                # Determine if doc is stale
                if "month" in age or "year" in age:
                    status = "⚠️"
                elif "week" in age:
                    status = "⚠️" if int(age.split()[0]) > 2 else "✅"
                else:
                    status = "✅"
                lines.append(f"  {doc}: Updated {age} {status}")
        lines.append("")
        
        # LLM-managed branches
        if self.is_git_repo:
            llm_branches = self.get_llm_managed_branches()
            has_llm_branches = any(llm_branches.values())
            
            if has_llm_branches:
                lines.append("🤖 LLM-Managed Branches:")
                
                if llm_branches['web_sync']:
                    lines.append(f"  Web Sync: {', '.join(llm_branches['web_sync'])} 🌐")
                
                if llm_branches['claude']:
                    lines.append(f"  Claude: {', '.join(llm_branches['claude'])}")
                
                if llm_branches['copilot']:
                    lines.append(f"  Copilot: {', '.join(llm_branches['copilot'])}")
                
                if llm_branches['gemini']:
                    lines.append(f"  Gemini: {', '.join(llm_branches['gemini'])}")
                
                if llm_branches['other_llm']:
                    lines.append(f"  Other LLM: {', '.join(llm_branches['other_llm'])}")
                
                if llm_branches['dangling']:
                    lines.append(f"  Dangling (cleanup needed): {', '.join(llm_branches['dangling'])} ⚠️")
                
                lines.append("")
        
        return "\n".join(lines)
