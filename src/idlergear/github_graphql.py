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
