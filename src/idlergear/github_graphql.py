"""GitHub GraphQL API client for IdlerGear.

Provides a clean interface to GitHub's GraphQL API v4 using the gh CLI.
This enables efficient queries for Projects v2, milestones, and other features.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class GitHubGraphQLError(Exception):
    """Error from GitHub GraphQL API."""


def _run_graphql_query(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query using gh CLI.

    Args:
        query: GraphQL query string
        variables: Optional query variables

    Returns:
        Parsed JSON response from GraphQL API

    Raises:
        GitHubGraphQLError: If query execution fails
    """
    args = ["gh", "api", "graphql", "-f", f"query={query}"]

    # Add variables if provided
    if variables:
        for key, value in variables.items():
            # Use -F for scalar values (String, Int, Boolean)
            # Use -f for complex types to avoid double-encoding
            if isinstance(value, (dict, list)):
                # For arrays/objects, pass as JSON string with -f (field)
                value_str = json.dumps(value)
                args.extend(["-f", f"{key}={value_str}"])
            else:
                # For scalars, use -F (raw field)
                args.extend(["-F", f"{key}={value}"])

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        response = json.loads(result.stdout)

        # Check for GraphQL errors
        if "errors" in response:
            errors = response["errors"]
            error_messages = [e.get("message", str(e)) for e in errors]
            raise GitHubGraphQLError(f"GraphQL errors: {'; '.join(error_messages)}")

        return response.get("data", {})

    except subprocess.CalledProcessError as e:
        raise GitHubGraphQLError(f"gh CLI error: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise GitHubGraphQLError("GraphQL query timed out after 30s")
    except json.JSONDecodeError as e:
        raise GitHubGraphQLError(f"Failed to parse GraphQL response: {e}")


class GitHubGraphQL:
    """GitHub GraphQL API client.

    Provides methods for common GraphQL queries used by IdlerGear.
    Uses gh CLI for authentication and execution.
    """

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a raw GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Response data from GraphQL API
        """
        return _run_graphql_query(query, variables)

    def get_repository_id(self, owner: str, name: str) -> str:
        """Get repository ID (required for Projects v2 queries).

        Args:
            owner: Repository owner
            name: Repository name

        Returns:
            Repository ID (node ID)
        """
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """
        data = self.query(query, {"owner": owner, "name": name})
        return data["repository"]["id"]

    def get_organization_id(self, login: str) -> str:
        """Get organization ID.

        Args:
            login: Organization login

        Returns:
            Organization ID (node ID)
        """
        query = """
        query($login: String!) {
          organization(login: $login) {
            id
          }
        }
        """
        data = self.query(query, {"login": login})
        return data["organization"]["id"]

    def get_user_id(self, login: str) -> str:
        """Get user ID.

        Args:
            login: User login

        Returns:
            User ID (node ID)
        """
        query = """
        query($login: String!) {
          user(login: $login) {
            id
          }
        }
        """
        data = self.query(query, {"login": login})
        return data["user"]["id"]

    def get_projects_v2(self, owner: str, first: int = 20) -> list[dict[str, Any]]:
        """Get Projects v2 for a user or organization.

        Args:
            owner: User or organization login
            first: Maximum number of projects to return

        Returns:
            List of project data
        """
        # Try as user first
        query = """
        query($owner: String!, $first: Int!) {
          user(login: $owner) {
            projectsV2(first: $first) {
              nodes {
                id
                number
                title
                shortDescription
                public
                closed
                url
                createdAt
                updatedAt
              }
            }
          }
        }
        """

        try:
            data = self.query(query, {"owner": owner, "first": first})
            if data.get("user"):
                return data["user"]["projectsV2"]["nodes"]
        except GitHubGraphQLError:
            pass

        # Try as organization
        query = """
        query($owner: String!, $first: Int!) {
          organization(login: $owner) {
            projectsV2(first: $first) {
              nodes {
                id
                number
                title
                shortDescription
                public
                closed
                url
                createdAt
                updatedAt
              }
            }
          }
        }
        """

        data = self.query(query, {"owner": owner, "first": first})
        return data["organization"]["projectsV2"]["nodes"]

    def get_project_v2(self, owner: str, number: int) -> dict[str, Any]:
        """Get a specific Project v2 by number.

        Args:
            owner: User or organization login
            number: Project number

        Returns:
            Project data
        """
        # Try as user first
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
              number
              title
              shortDescription
              public
              closed
              url
              createdAt
              updatedAt
              fields(first: 20) {
                nodes {
                  ... on ProjectV2Field {
                    id
                    name
                    dataType
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    dataType
                    options {
                      id
                      name
                    }
                  }
                }
              }
              items(first: 100) {
                nodes {
                  id
                  content {
                    ... on Issue {
                      number
                      title
                      state
                    }
                    ... on PullRequest {
                      number
                      title
                      state
                    }
                  }
                }
              }
            }
          }
        }
        """

        try:
            data = self.query(query, {"owner": owner, "number": number})
            if data.get("user", {}).get("projectV2"):
                return data["user"]["projectV2"]
        except GitHubGraphQLError:
            pass

        # Try as organization
        query = query.replace("user(", "organization(")
        data = self.query(query, {"owner": owner, "number": number})
        return data["organization"]["projectV2"]

    def get_milestones(
        self,
        owner: str,
        repo: str,
        state: str = "OPEN",
        first: int = 20,
    ) -> list[dict[str, Any]]:
        """Get milestones for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Milestone state (OPEN, CLOSED)
            first: Maximum number to return

        Returns:
            List of milestone data with issue counts
        """
        # Note: states array is hardcoded in query to avoid enum serialization issues
        query = f"""
        query($owner: String!, $repo: String!, $first: Int!) {{
          repository(owner: $owner, name: $repo) {{
            milestones(states: [{state}], first: $first) {{
              nodes {{
                id
                number
                title
                description
                state
                dueOn
                createdAt
                updatedAt
                closedAt
                url
                issues {{
                  totalCount
                }}
              }}
            }}
          }}
        }}
        """

        data = self.query(
            query,
            {
                "owner": owner,
                "repo": repo,
                "first": first,
            },
        )
        return data["repository"]["milestones"]["nodes"]

    def get_repository_info(self, owner: str, name: str) -> dict[str, Any]:
        """Get repository information including owner type.

        Args:
            owner: Repository owner
            name: Repository name

        Returns:
            Repository data including ID, name, and owner information
        """
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
            name
            owner {
              login
              ... on User {
                id
              }
              ... on Organization {
                id
              }
            }
            url
            description
          }
        }
        """
        data = self.query(query, {"owner": owner, "name": name})
        return data["repository"]

    def add_issue_to_project(
        self, project_id: str, issue_id: str
    ) -> dict[str, Any]:
        """Add an issue to a GitHub Project v2.

        Args:
            project_id: Project node ID (from get_project_v2)
            issue_id: Issue node ID (not issue number!)

        Returns:
            Project item data including item ID

        Raises:
            GitHubGraphQLError: If mutation fails
        """
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {
            projectId: $projectId
            contentId: $contentId
          }) {
            item {
              id
            }
          }
        }
        """

        data = self.query(mutation, {
            "projectId": project_id,
            "contentId": issue_id
        })
        return data["addProjectV2ItemById"]["item"]

    def get_issue_id(self, owner: str, repo: str, issue_number: int) -> str:
        """Get issue node ID from issue number.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue node ID
        """
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
            }
          }
        }
        """

        data = self.query(query, {
            "owner": owner,
            "repo": repo,
            "number": issue_number
        })
        return data["repository"]["issue"]["id"]

    def update_project_item_field_text(
        self, project_id: str, item_id: str, field_id: str, value: str
    ) -> dict[str, Any]:
        """Update a text field on a project item.

        Args:
            project_id: Project node ID
            item_id: Project item ID
            field_id: Field node ID
            value: Text value to set

        Returns:
            Updated project item
        """
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: {
              text: $value
            }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        data = self.query(mutation, {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": value
        })
        return data["updateProjectV2ItemFieldValue"]["projectV2Item"]

    def update_project_item_field_date(
        self, project_id: str, item_id: str, field_id: str, value: str
    ) -> dict[str, Any]:
        """Update a date field on a project item.

        Args:
            project_id: Project node ID
            item_id: Project item ID
            field_id: Field node ID
            value: Date string in ISO 8601 format (YYYY-MM-DD)

        Returns:
            Updated project item
        """
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: Date!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: {
              date: $value
            }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        data = self.query(mutation, {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": value
        })
        return data["updateProjectV2ItemFieldValue"]["projectV2Item"]

    def update_project_item_field_single_select(
        self, project_id: str, item_id: str, field_id: str, option_id: str
    ) -> dict[str, Any]:
        """Update a single-select field on a project item.

        Args:
            project_id: Project node ID
            item_id: Project item ID
            field_id: Field node ID
            option_id: Option node ID (from field options)

        Returns:
            Updated project item
        """
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: {
              singleSelectOptionId: $optionId
            }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        data = self.query(mutation, {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "optionId": option_id
        })
        return data["updateProjectV2ItemFieldValue"]["projectV2Item"]

    def get_project_item_by_content(
        self, project_id: str, owner: str, repo: str, issue_number: int
    ) -> dict[str, Any] | None:
        """Get project item for a specific issue.

        Args:
            project_id: Project node ID
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Project item data or None if not found
        """
        # First get the issue ID
        issue_id = self.get_issue_id(owner, repo, issue_number)

        query = """
        query($projectId: ID!, $first: Int!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: $first) {
                nodes {
                  id
                  content {
                    ... on Issue {
                      id
                      number
                    }
                  }
                }
              }
            }
          }
        }
        """

        data = self.query(query, {"projectId": project_id, "first": 100})
        items = data.get("node", {}).get("items", {}).get("nodes", [])

        for item in items:
            content = item.get("content", {})
            if content.get("id") == issue_id:
                return item

        return None
