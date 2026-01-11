"""Tests for context gathering and token efficiency."""

from idlergear.context import gather_context, truncate_lines, truncate_text


def test_truncate_text():
    """Test text truncation."""
    # No truncation needed
    assert truncate_text("hello", 10) == "hello"

    # Truncation needed
    assert truncate_text("hello world!", 8) == "hello..."

    # None handling
    assert truncate_text(None, 10) is None

    # No limit
    assert truncate_text("hello world", None) == "hello world"


def test_truncate_lines():
    """Test line truncation."""
    text = "line1\nline2\nline3\nline4"

    # No truncation needed
    assert truncate_lines(text, 5) == text

    # Truncation needed
    assert truncate_lines(text, 2) == "line1\nline2\n..."

    # None handling
    assert truncate_lines(None, 10) is None

    # No limit
    assert truncate_lines(text, None) == text


def test_context_modes():
    """Test different context modes produce expected output sizes."""
    modes = ["minimal", "standard", "detailed", "full"]
    sizes = {}

    for mode in modes:
        ctx = gather_context(mode=mode)
        # Estimate size by counting characters in all text fields
        size = 0
        if ctx.vision:
            size += len(ctx.vision)
        if ctx.current_plan and ctx.current_plan.get("body"):
            size += len(ctx.current_plan["body"])
        for task in ctx.open_tasks:
            if task.get("body"):
                size += len(task["body"])
        sizes[mode] = size

    # Verify modes are progressively larger
    assert sizes["minimal"] < sizes["standard"]
    assert sizes["standard"] < sizes["detailed"]


def test_minimal_mode():
    """Test minimal mode produces small context."""
    ctx = gather_context(mode="minimal")

    # Should have limited tasks
    assert len(ctx.open_tasks) <= 5

    # Should have no notes (just count)
    assert len(ctx.recent_notes) == 0

    # Vision should be truncated
    if ctx.vision:
        assert len(ctx.vision) <= 203  # 200 + "..."


def test_standard_mode():
    """Test standard mode is balanced."""
    ctx = gather_context(mode="standard")

    # Should have reasonable task count
    assert len(ctx.open_tasks) <= 10

    # Should have some notes
    assert len(ctx.recent_notes) <= 5

    # Vision should be moderately truncated
    if ctx.vision:
        assert len(ctx.vision) <= 503  # 500 + "..."


def test_full_mode():
    """Test full mode has no limits."""
    ctx = gather_context(mode="full")

    # Vision should not be truncated
    # (We can't assert exact length, just that it exists if there's a vision file)
    assert ctx.vision is None or isinstance(ctx.vision, str)


def test_mode_task_body_truncation():
    """Test that task bodies are truncated based on mode."""
    # Create a project with tasks that have long bodies
    # This is implicitly tested by the mode tests above
    # The actual truncation happens in gather_context

    ctx_minimal = gather_context(mode="minimal")
    ctx_standard = gather_context(mode="standard")

    # In minimal mode, task bodies should be empty or very short
    for task in ctx_minimal.open_tasks:
        if task.get("body"):
            # Should be truncated to 0 lines = removed or empty
            lines = task["body"].split("\n")
            assert len(lines) <= 1  # Just "..." or empty


def test_context_json_serialization():
    """Test that context can be serialized to JSON."""
    from idlergear.context import format_context_json
    import json

    ctx = gather_context(mode="minimal")
    ctx_dict = format_context_json(ctx)

    # Should be JSON serializable
    json_str = json.dumps(ctx_dict)
    assert isinstance(json_str, str)

    # Should deserialize back
    reloaded = json.loads(json_str)
    assert isinstance(reloaded, dict)
    assert "vision" in reloaded
    assert "open_tasks" in reloaded
