"""MCP handlers for script generation and process management."""

from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.runs import start_run
from idlergear.script_generator import (
    generate_dev_script,
    generate_script_from_template,
    save_script,
)


def handle_script_generate(arguments: dict[str, Any]) -> str:
    """Handle idlergear_script_generate tool call."""
    script_name = arguments["script_name"]
    command = arguments["command"]
    output_path = arguments.get("output_path")
    venv_path = arguments.get("venv_path")
    requirements = arguments.get("requirements", [])
    env_vars = arguments.get("env_vars", {})
    stream_logs = arguments.get("stream_logs", False)

    project_root = find_idlergear_root()
    if project_root is None:
        return "Error: Not in an IdlerGear project. Run 'idlergear init' first."

    try:
        # Generate script
        script_content = generate_dev_script(
            script_name,
            command,
            venv_path=venv_path,
            requirements=requirements if requirements else None,
            env_vars=env_vars if env_vars else None,
            register_with_daemon=True,
            stream_logs=stream_logs,
            project_path=project_root,
        )

        # Determine output path
        if output_path is None:
            scripts_dir = project_root / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            output_path = str(scripts_dir / f"{script_name}.sh")

        output_file = Path(output_path)
        save_script(script_content, output_file, make_executable=True)

        features = ["Auto-registers with IdlerGear daemon"]
        if stream_logs:
            features.append("Streams logs to daemon")
        if venv_path:
            features.append(f"Activates virtualenv: {venv_path}")
        if requirements:
            features.append(f"Installs packages: {', '.join(requirements)}")
        if env_vars:
            features.append(f"Sets environment variables: {', '.join(env_vars.keys())}")

        rel_path = output_file.relative_to(project_root)

        return f"""✓ Generated script: {output_file}

Run with: ./{rel_path}

Features:
{chr(10).join(f'  • {f}' for f in features)}

The script will:
1. Set up the development environment
2. Register as an agent with the IdlerGear daemon
3. Provide helper functions (idlergear_send, idlergear_log, idlergear_status)
4. Auto-cleanup on exit

You can now run this script in a separate terminal and it will coordinate with the IdlerGear daemon.
"""

    except Exception as e:
        return f"Error generating script: {e}"


def handle_script_from_template(arguments: dict[str, Any]) -> str:
    """Handle idlergear_script_from_template tool call."""
    template = arguments["template"]
    script_name = arguments["script_name"]
    output_path = arguments.get("output_path")
    venv_path = arguments.get("venv_path")
    env_vars = arguments.get("env_vars", {})

    project_root = find_idlergear_root()
    if project_root is None:
        return "Error: Not in an IdlerGear project. Run 'idlergear init' first."

    try:
        # Generate from template
        script_content = generate_script_from_template(
            template,
            script_name,
            venv_path=venv_path,
            env_vars=env_vars if env_vars else None,
            register_with_daemon=True,
            stream_logs=False,
            project_path=project_root,
        )

        # Determine output path
        if output_path is None:
            scripts_dir = project_root / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            output_path = str(scripts_dir / f"{script_name}.sh")

        output_file = Path(output_path)
        save_script(script_content, output_file, make_executable=True)

        rel_path = output_file.relative_to(project_root)

        return f"""✓ Generated script from template '{template}': {output_file}

Run with: ./{rel_path}

The script includes:
  • Pre-configured command for {template}
  • Required dependencies
  • Auto-registration with IdlerGear daemon
  • Helper functions for coordination

Run this in a separate terminal to start the {template} environment.
"""

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error generating script from template: {e}"


def handle_run_with_daemon(arguments: dict[str, Any]) -> str:
    """Handle idlergear_run_with_daemon tool call."""
    command = arguments["command"]
    name = arguments.get("name")
    register = arguments.get("register", True)
    stream_logs = arguments.get("stream_logs", False)

    project_root = find_idlergear_root()
    if project_root is None:
        return "Error: Not in an IdlerGear project. Run 'idlergear init' first."

    try:
        run = start_run(
            command,
            name=name,
            register_with_daemon=register,
            stream_logs=stream_logs,
        )

        features = []
        if register:
            features.append(f"Registered as agent: {run.get('agent_id', 'N/A')}")
        if stream_logs:
            features.append("Streaming logs to daemon")

        return f"""✓ Started background process: {run['name']}

  PID:     {run['pid']}
  Command: {run['command']}
  Status:  {run['status']}

{chr(10).join(f'  • {f}' for f in features) if features else ''}

View logs: idlergear run logs {run['name']}
Stop:      idlergear run stop {run['name']}
Status:    idlergear run status {run['name']}

{'The process is registered with the daemon and visible to other AI agents.' if register else ''}
"""

    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error starting run: {e}"
