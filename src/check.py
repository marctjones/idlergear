"""
Check command: Analyze project for best practice adherence.
"""
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from src.status import ProjectStatus


class ProjectChecker:
    """Analyze project for best practice violations and provide nudges."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.status = ProjectStatus(project_path)
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.suggestions: List[Dict] = []
    
    def check_test_coverage(self) -> None:
        """Check if tests are being added with code changes."""
        if not self.status.is_git_repo:
            return
        
        # Get last 5 commits
        commits = self.status.get_recent_commits(count=5)
        if not commits:
            return
        
        # Count commits without "test" in message
        non_test_commits = 0
        for commit in commits:
            if 'test' not in commit['message'].lower():
                non_test_commits += 1
        
        if non_test_commits >= 3:
            self.warnings.append({
                'category': 'Testing',
                'message': f"You haven't mentioned tests in the last {non_test_commits} commits",
                'suggestion': 'Consider following TDD: write tests before implementing features'
            })
    
    def check_charter_freshness(self) -> None:
        """Check if charter documents are stale."""
        charter_docs = ['VISION.md', 'TODO.md', 'IDEAS.md', 'DESIGN.md']
        
        for doc in charter_docs:
            age = self.status.get_charter_doc_age(doc)
            
            if age == "Not found":
                if doc == 'TODO.md':
                    self.issues.append({
                        'category': 'Documentation',
                        'message': f'{doc} not found',
                        'suggestion': 'Create a TODO.md to track tasks and progress'
                    })
            elif age and ('month' in age or 'year' in age):
                self.warnings.append({
                    'category': 'Documentation',
                    'message': f'{doc} hasn\'t been updated in {age}',
                    'suggestion': f'Review and update {doc} to reflect current project state'
                })
    
    def check_uncommitted_work(self) -> None:
        """Check for excessive uncommitted changes."""
        if not self.status.is_git_repo:
            return
        
        uncommitted = self.status.get_uncommitted_changes()
        
        if uncommitted >= 10:
            self.warnings.append({
                'category': 'Git Hygiene',
                'message': f'You have {uncommitted} uncommitted files',
                'suggestion': 'Commit your work frequently in small, logical chunks'
            })
        elif uncommitted >= 5:
            self.suggestions.append({
                'category': 'Git Hygiene',
                'message': f'{uncommitted} uncommitted files',
                'suggestion': 'Consider committing your progress'
            })
    
    def check_dangling_branches(self) -> None:
        """Check for stale branches that need cleanup."""
        if not self.status.is_git_repo:
            return
        
        llm_branches = self.status.get_llm_managed_branches()
        
        if llm_branches['dangling']:
            self.warnings.append({
                'category': 'Branch Management',
                'message': f"{len(llm_branches['dangling'])} dangling branch(es): {', '.join(llm_branches['dangling'][:3])}",
                'suggestion': 'Clean up old branches with: idlergear branches cleanup'
            })
    
    def check_web_sync_status(self) -> None:
        """Check if there are unsynced web branches."""
        if not self.status.is_git_repo:
            return
        
        llm_branches = self.status.get_llm_managed_branches()
        
        if llm_branches['web_sync']:
            self.suggestions.append({
                'category': 'Web Sync',
                'message': f"Web sync branch exists: {', '.join(llm_branches['web_sync'])}",
                'suggestion': 'Remember to sync: idlergear sync pull'
            })
    
    def check_project_structure(self) -> None:
        """Check for missing common project files."""
        if not self.status.git_root:
            return
        
        important_files = {
            'README.md': 'Create a README.md to document your project',
            'DEVELOPMENT.md': 'Add DEVELOPMENT.md for development practices',
            '.gitignore': 'Add .gitignore to exclude unnecessary files'
        }
        
        for filename, suggestion in important_files.items():
            filepath = self.status.git_root / filename
            if not filepath.exists():
                self.suggestions.append({
                    'category': 'Project Structure',
                    'message': f'{filename} not found',
                    'suggestion': suggestion
                })
    
    def check_llm_coordination(self) -> None:
        """Check for potential multi-LLM coordination issues."""
        if not self.status.is_git_repo:
            return
        
        llm_branches = self.status.get_llm_managed_branches()
        
        # Count active LLM branches (excluding web_sync and dangling)
        active_llm = sum(
            len(branches) 
            for category, branches in llm_branches.items() 
            if category not in ['web_sync', 'dangling'] and branches
        )
        
        if active_llm >= 2:
            branch_types = [
                category for category, branches in llm_branches.items()
                if category not in ['web_sync', 'dangling'] and branches
            ]
            self.suggestions.append({
                'category': 'LLM Coordination',
                'message': f'Multiple LLM branches detected: {", ".join(branch_types)}',
                'suggestion': 'Use idlergear sync to coordinate between different LLM tools'
            })
    
    def run_all_checks(self) -> None:
        """Run all checks."""
        self.check_test_coverage()
        self.check_charter_freshness()
        self.check_uncommitted_work()
        self.check_dangling_branches()
        self.check_web_sync_status()
        self.check_project_structure()
        self.check_llm_coordination()
    
    def format_report(self) -> str:
        """Format check results as a readable report."""
        lines = []
        
        # Header
        lines.append("")
        lines.append(f"🔍 Project Health Check: {self.status.get_project_name()}")
        lines.append("=" * 60)
        lines.append("")
        
        # Issues (critical)
        if self.issues:
            lines.append("❌ Issues (need attention):")
            for issue in self.issues:
                lines.append(f"  • [{issue['category']}] {issue['message']}")
                lines.append(f"    💡 {issue['suggestion']}")
                lines.append("")
        
        # Warnings (important)
        if self.warnings:
            lines.append("⚠️  Warnings:")
            for warning in self.warnings:
                lines.append(f"  • [{warning['category']}] {warning['message']}")
                lines.append(f"    💡 {warning['suggestion']}")
                lines.append("")
        
        # Suggestions (nice to have)
        if self.suggestions:
            lines.append("💡 Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  • [{suggestion['category']}] {suggestion['message']}")
                lines.append(f"    ➜ {suggestion['suggestion']}")
                lines.append("")
        
        # Summary
        if not self.issues and not self.warnings and not self.suggestions:
            lines.append("✅ Everything looks good! No issues found.")
            lines.append("")
        else:
            total = len(self.issues) + len(self.warnings) + len(self.suggestions)
            lines.append("-" * 60)
            lines.append(f"Total: {len(self.issues)} issue(s), {len(self.warnings)} warning(s), {len(self.suggestions)} suggestion(s)")
            lines.append("")
        
        return "\n".join(lines)
