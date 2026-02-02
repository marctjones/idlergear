"""Output formatting for IdlerGear CLI."""

import json
import sys

import typer


def is_interactive() -> bool:
    """Check if the current session is interactive (i.e., a TTY)."""
    return sys.stdout.isatty()


def display(data: any, output_format: str, data_type: str) -> None:
    """
    Display data in the specified format.

    Args:
        data: The data to display (e.g., list of dicts, a dict).
        output_format: The format, typically 'human' or 'json'.
        data_type: A hint for human formatting (e.g., 'tasks', 'vision').
    """
    if output_format == "json":
        print_json(data)
    else:
        print_human(data, data_type)


def print_json(data: any) -> None:
    """Print data as a JSON object."""
    if data is None:
        typer.echo("null")
    elif isinstance(data, (str, bytes)):
        # If the data is already a string, just print it.
        # This handles cases where a command just returns a message.
        typer.echo(data)
    else:
        typer.echo(json.dumps(data, indent=2))


def print_human(data: any, data_type: str, **kwargs) -> None:
    """Print data in a human-readable format."""
    formatters = {
        "tasks": format_task_list,
        "task": format_task,
        "vision": format_vision,
        "notes": format_note_list,
        "note": format_note,
        "plans": format_plan_list,
        "plan": format_plan,
        "references": format_reference_list,
        "reference": format_reference,
        "search": format_search_results,
        "status": format_status,
        "status_summary": format_status_summary,
        "context": format_context,
    }
    formatter = formatters.get(data_type)

    if formatter:
        formatter(data, **kwargs)
    elif isinstance(data, list) and not data:
        # Handle empty lists gracefully for any data type
        typer.echo(f"No {data_type} found.")
    elif isinstance(data, str):
        typer.echo(data)
    elif data is None:
        pass  # Do nothing for None
    else:
        # Default fallback for unknown types
        typer.echo(str(data))


def format_task_list(tasks: list[dict]) -> None:
    """Format a list of tasks for human-readable output."""
    if not tasks:
        typer.echo("No tasks found.")
        return

    for task in tasks:
        state_icon = "o" if task["state"] == "open" else "x"
        labels_str = f" [{', '.join(task['labels'])}]" if task.get("labels") else ""
        priority_str = f" !{task['priority']}" if task.get("priority") else ""
        due_str = f" @{task['due']}" if task.get("due") else ""
        typer.echo(
            f"  [{state_icon}] #{task['id']:<4} {task['title']}{priority_str}{due_str}{labels_str}"
        )


def format_task(task: dict | None) -> None:
    """Format a single task for human-readable output."""
    if task is None:
        typer.secho("Task not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    state_color = typer.colors.GREEN if task["state"] == "open" else typer.colors.RED
    typer.echo(f"Task #{task['id']}: {task['title']}")
    typer.secho(f"State: {task['state']}", fg=state_color)
    if task.get("priority"):
        priority_colors = {
            "high": typer.colors.RED,
            "medium": typer.colors.YELLOW,
            "low": typer.colors.BLUE,
        }
        typer.secho(
            f"Priority: {task['priority']}",
            fg=priority_colors.get(task["priority"], typer.colors.WHITE),
        )
    if task.get("due"):
        typer.echo(f"Due: {task['due']}")
    if task.get("labels"):
        typer.echo(f"Labels: {', '.join(task['labels'])}")
    if task.get("assignees"):
        typer.echo(f"Assignees: {', '.join(task['assignees'])}")
    created = task.get("created") or task.get("created_at")
    if created:
        typer.echo(f"Created: {created}")
    if task.get("github_issue"):
        typer.echo(f"GitHub: #{task['github_issue']}")
    typer.echo("")
    if task.get("body"):
        typer.echo(task["body"])


def format_vision(vision: str | None) -> None:
    """Format the project vision for human-readable output."""
    if vision is None or not vision.strip():
        typer.echo("No vision set. Use 'idlergear vision edit' to set one.")
        return
    typer.echo(vision)


def format_note_list(notes: list[dict]) -> None:
    """Format a list of notes for human-readable output."""
    if not notes:
        typer.echo("No notes found.")
        return

    for note in notes:
        preview = note["content"][:50].replace("\n", " ")
        if len(note["content"]) > 50:
            preview += "..."
        tag_str = f" [{', '.join(note['tags'])}]" if note.get("tags") else ""
        typer.echo(f"  #{note['id']:<4}{tag_str}  {preview}")


def format_note(note: dict | None) -> None:
    """Format a single note for human-readable output."""
    if note is None:
        typer.secho("Note not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Note #{note['id']}")
    if note.get("tags"):
        typer.echo(f"Tags: {', '.join(note['tags'])}")
    typer.echo(f"Created: {note['created']}")
    typer.echo("")
    typer.echo(note["content"])


def format_plan_list(plans: list[dict]) -> None:
    """Format a list of plans for human-readable output."""
    if not plans:
        typer.echo("No plans found.")
        return

    for plan in plans:
        marker = "*" if plan.get("is_current") else " "
        typer.echo(f"  {marker} {plan['name']}: {plan['title']}")


def format_plan(plan: dict | None) -> None:
    """Format a single plan for human-readable output."""
    if plan is None:
        # This case is handled in the command itself for a better message.
        return

    typer.echo(f"Plan: {plan['name']}")
    typer.echo(f"Description: {plan['description']}")
    typer.echo(f"Status: {plan['status']}")
    typer.echo(f"Type: {plan['type']}")
    typer.echo(f"Created: {plan['created']}")
    if plan.get("github_project_id"):
        typer.echo(f"GitHub: Project {plan['github_project_id']}")
    if plan.get("milestone"):
        typer.echo(f"Milestone: {plan['milestone']}")

    # Show file and task counts
    if plan.get("files"):
        typer.echo(f"Files: {len(plan['files'])}")
    if plan.get("tasks"):
        typer.echo(f"Tasks: {len(plan['tasks'])}")
    if plan.get("sub_plans"):
        typer.echo(f"Sub-plans: {len(plan['sub_plans'])}")


def format_reference_list(refs: list[dict]) -> None:
    """Format a list of reference documents for human-readable output."""
    if not refs:
        typer.echo("No reference documents found.")
        return

    for ref in refs:
        typer.echo(f"  {ref['title']}")


def format_reference(ref: dict | None) -> None:
    """Format a single reference document for human-readable output."""
    if ref is None:
        typer.secho("Reference not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Reference: {ref['title']}")
    typer.echo(f"Created: {ref['created']}")
    typer.echo(f"Updated: {ref['updated']}")
    typer.echo("")
    if ref.get("body"):
        typer.echo(ref["body"])


def format_search_results(results: list[dict], **kwargs) -> None:
    """Format search results for human-readable output."""
    if not results:
        typer.echo("No results found.")
        return

    query = results[0].get("_query", "")  # Extract query if available
    typer.echo(f"Found {len(results)} result(s) for '{query}':\n")

    by_type: dict[str, list] = {}
    for result in results:
        t = result["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(result)

    type_colors = {
        "task": typer.colors.GREEN,
        "note": typer.colors.YELLOW,
        "reference": typer.colors.MAGENTA,
        "plan": typer.colors.BLUE,
    }

    for type_name, items in by_type.items():
        typer.secho(
            f"{type_name.upper()}S ({len(items)})",
            fg=type_colors.get(type_name, typer.colors.WHITE),
            bold=True,
        )
        for item in items:
            id_str = f"#{item.get('id', item.get('name', '?'))}"
            title = item.get("title", "")
            preview = item.get("preview", "")[:60]
            typer.echo(f"  {id_str:8}  {title}")
            if preview and preview != title:
                typer.echo(f"            {preview}")
        typer.echo("")


def format_context(ctx: "ProjectContext", **kwargs) -> None:
    """Format project context by calling the original formatter."""
    from idlergear.context import format_context as original_formatter

    verbose = kwargs.get("verbose", False)
    typer.echo(original_formatter(ctx, verbose=verbose))


def format_status(status: "ProjectStatus", **kwargs) -> None:
    """Format detailed status dashboard by calling the original formatter."""
    from idlergear.status import format_detailed_status

    typer.echo(format_detailed_status(status))


def format_status_summary(status: "ProjectStatus", **kwargs) -> None:
    """Format status summary by calling the original summary method."""
    typer.echo(status.summary())
