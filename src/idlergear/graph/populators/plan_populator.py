"""Populates graph database with Plan Objects."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from idlergear.config import find_idlergear_root
from idlergear.plans import list_plans

from ..database import GraphDatabase


class PlanPopulator:
    """Populates graph database with plans from Plan Objects system.

    Indexes plans as Plan nodes and creates relationships:
    - Plan → File (PLAN_CONTAINS_FILE)
    - Plan → Task (PART_OF_PLAN)
    - Plan → Reference (PLAN_REFERENCES)
    - Plan → Plan (PLAN_PARENT_OF, PLAN_SUPERSEDES)

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = PlanPopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize plan populator.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self._processed_plans: Set[str] = set()

    def populate(
        self,
        status: Optional[str] = None,
        type_filter: Optional[str] = None,
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with plans.

        Args:
            status: Status filter ('active', 'completed', 'deprecated', 'archived')
            type_filter: Type filter ('ephemeral', 'feature', 'roadmap', 'initiative')
            incremental: If True, skip plans already in database

        Returns:
            Dictionary with counts: plans, relationships
        """
        # Find IdlerGear root
        root = find_idlergear_root(self.project_path)
        if root is None:
            return {"plans": 0, "updated": 0, "relationships": 0}

        # List plans
        plans = list_plans(root, status=status, type_filter=type_filter)

        plans_added = 0
        plans_updated = 0
        relationships_added = 0

        conn = self.db.get_connection()

        for plan in plans:
            # Skip if already processed (incremental mode)
            if incremental and self._is_plan_in_db(plan.name):
                # Update if plan was modified
                if self._should_update_plan(plan):
                    self._update_plan(plan)
                    plans_updated += 1
                # Always update relationships (files/tasks may change)
                relationships_added += self._create_relationships(plan)
                continue

            # Insert plan node
            self._insert_plan(plan)
            plans_added += 1

            # Create relationships
            relationships_added += self._create_relationships(plan)

        return {
            "plans": plans_added,
            "updated": plans_updated,
            "relationships": relationships_added,
        }

    def _is_plan_in_db(self, plan_name: str) -> bool:
        """Check if plan already exists in database."""
        conn = self.db.get_connection()
        try:
            result = conn.execute(
                "MATCH (p:Plan {name: $name}) RETURN p", {"name": plan_name}
            )
            return result.has_next()
        except Exception:
            return False

    def _should_update_plan(self, plan) -> bool:
        """Check if plan should be updated (status changed, etc.)."""
        conn = self.db.get_connection()

        try:
            result = conn.execute(
                "MATCH (p:Plan {name: $name}) RETURN p.status as status",
                {"name": plan.name},
            )
            if result.has_next():
                row = result.get_next()
                db_status = row[0]
                return db_status != plan.status
            return False
        except Exception:
            return False

    def _insert_plan(self, plan) -> None:
        """Insert plan node into database."""
        conn = self.db.get_connection()

        # Convert timestamps to datetime objects
        created_at = self._parse_timestamp(plan.created)
        completed_at = self._parse_timestamp(plan.completed_at)
        deprecated_at = self._parse_timestamp(plan.deprecated_at)
        archived_at = self._parse_timestamp(plan.archived_at)

        query = """
            CREATE (p:Plan {
                name: $name,
                description: $description,
                status: $status,
                type: $type,
                milestone: $milestone,
                auto_archive: $auto_archive,
                github_milestone_id: $github_milestone_id,
                github_project_id: $github_project_id,
                created_at: $created_at,
                completed_at: $completed_at,
                deprecated_at: $deprecated_at,
                archived_at: $archived_at
            })
        """

        conn.execute(
            query,
            {
                "name": plan.name,
                "description": plan.description,
                "status": plan.status,
                "type": plan.type,
                "milestone": plan.milestone,
                "auto_archive": plan.auto_archive,
                "github_milestone_id": plan.github_milestone_id,
                "github_project_id": plan.github_project_id,
                "created_at": created_at,
                "completed_at": completed_at,
                "deprecated_at": deprecated_at,
                "archived_at": archived_at,
            },
        )

    def _update_plan(self, plan) -> None:
        """Update existing plan node."""
        conn = self.db.get_connection()

        completed_at = self._parse_timestamp(plan.completed_at)
        deprecated_at = self._parse_timestamp(plan.deprecated_at)
        archived_at = self._parse_timestamp(plan.archived_at)

        query = """
            MATCH (p:Plan {name: $name})
            SET p.description = $description,
                p.status = $status,
                p.milestone = $milestone,
                p.completed_at = $completed_at,
                p.deprecated_at = $deprecated_at,
                p.archived_at = $archived_at
        """

        conn.execute(
            query,
            {
                "name": plan.name,
                "description": plan.description,
                "status": plan.status,
                "milestone": plan.milestone,
                "completed_at": completed_at,
                "deprecated_at": deprecated_at,
                "archived_at": archived_at,
            },
        )

    def _create_relationships(self, plan) -> int:
        """Create all relationships for a plan."""
        count = 0
        count += self._create_file_relationships(plan)
        count += self._create_task_relationships(plan)
        count += self._create_reference_relationships(plan)
        count += self._create_plan_relationships(plan)
        return count

    def _create_file_relationships(self, plan) -> int:
        """Create Plan → File relationships."""
        conn = self.db.get_connection()
        count = 0

        # Delete existing relationships
        conn.execute(
            """
            MATCH (p:Plan {name: $name})-[r:PLAN_CONTAINS_FILE]->()
            DELETE r
        """,
            {"name": plan.name},
        )

        # Create relationships for active files
        for file_path in plan.files:
            try:
                # Ensure file node exists first
                conn.execute(
                    "MERGE (f:File {path: $path})", {"path": file_path}
                )

                # Create relationship
                conn.execute(
                    """
                    MATCH (p:Plan {name: $plan_name})
                    MATCH (f:File {path: $file_path})
                    CREATE (p)-[:PLAN_CONTAINS_FILE {deprecated: false}]->(f)
                """,
                    {"plan_name": plan.name, "file_path": file_path},
                )
                count += 1
            except Exception:
                pass  # File may not exist in graph yet

        # Create relationships for deprecated files
        for file_path in plan.deprecated_files:
            try:
                conn.execute(
                    "MERGE (f:File {path: $path})", {"path": file_path}
                )

                conn.execute(
                    """
                    MATCH (p:Plan {name: $plan_name})
                    MATCH (f:File {path: $file_path})
                    CREATE (p)-[:PLAN_CONTAINS_FILE {deprecated: true}]->(f)
                """,
                    {"plan_name": plan.name, "file_path": file_path},
                )
                count += 1
            except Exception:
                pass

        return count

    def _create_task_relationships(self, plan) -> int:
        """Create Task → Plan relationships (reverse of query direction)."""
        conn = self.db.get_connection()
        count = 0

        for task_id in plan.tasks:
            try:
                # Check if task exists
                result = conn.execute(
                    "MATCH (t:Task {id: $id}) RETURN t", {"id": task_id}
                )
                if not result.has_next():
                    continue

                # Create relationship if not exists
                conn.execute(
                    """
                    MATCH (t:Task {id: $task_id})
                    MATCH (p:Plan {name: $plan_name})
                    MERGE (t)-[:PART_OF_PLAN]->(p)
                """,
                    {"task_id": task_id, "plan_name": plan.name},
                )
                count += 1
            except Exception:
                pass

        return count

    def _create_reference_relationships(self, plan) -> int:
        """Create Plan → Reference relationships."""
        conn = self.db.get_connection()
        count = 0

        for ref_id in plan.references:
            try:
                # Check if reference exists (references use title as ID)
                result = conn.execute(
                    "MATCH (r:Reference {id: $id}) RETURN r", {"id": ref_id}
                )
                if not result.has_next():
                    continue

                # Create relationship
                conn.execute(
                    """
                    MATCH (p:Plan {name: $plan_name})
                    MATCH (r:Reference {id: $ref_id})
                    MERGE (p)-[:PLAN_REFERENCES]->(r)
                """,
                    {"plan_name": plan.name, "ref_id": ref_id},
                )
                count += 1
            except Exception:
                pass

        return count

    def _create_plan_relationships(self, plan) -> int:
        """Create Plan → Plan relationships (parent, successor)."""
        conn = self.db.get_connection()
        count = 0

        # Parent relationship
        if plan.parent_plan:
            try:
                conn.execute(
                    """
                    MATCH (parent:Plan {name: $parent_name})
                    MATCH (child:Plan {name: $child_name})
                    MERGE (parent)-[:PLAN_PARENT_OF]->(child)
                """,
                    {"parent_name": plan.parent_plan, "child_name": plan.name},
                )
                count += 1
            except Exception:
                pass

        # Successor relationship (supersedes)
        if plan.successor_plan:
            try:
                deprecated_at = self._parse_timestamp(plan.deprecated_at)
                conn.execute(
                    """
                    MATCH (old:Plan {name: $old_name})
                    MATCH (new:Plan {name: $new_name})
                    MERGE (new)-[:PLAN_SUPERSEDES {deprecated_at: $deprecated_at}]->(old)
                """,
                    {
                        "old_name": plan.name,
                        "new_name": plan.successor_plan,
                        "deprecated_at": deprecated_at,
                    },
                )
                count += 1
            except Exception:
                pass

        return count

    @staticmethod
    def _parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            return None
