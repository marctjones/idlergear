"""Relevance scoring and memory decay algorithms.

This module provides algorithms for calculating relevance scores based on:
- Time since creation (decay)
- Time since last access (decay)
- Access frequency (boost)

The relevance score determines which knowledge items (tasks, notes) should be
included in context generation, enabling automatic filtering of stale content.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Literal

DecayFunction = Literal["exponential", "linear", "step"]


def calculate_relevance(
    created: datetime,
    accessed: datetime | None = None,
    access_count: int = 0,
    decay_function: DecayFunction = "exponential",
    half_life_days: int = 30,
    access_boost: float = 0.1,
) -> float:
    """Calculate relevance score (0.0-1.0) for a knowledge item.

    The relevance score is calculated based on:
    1. Time decay - items get less relevant over time
    2. Access boost - frequently accessed items get a relevance boost

    Args:
        created: When the item was created
        accessed: When the item was last accessed (None if never accessed)
        access_count: Number of times the item has been accessed
        decay_function: Type of decay to apply ("exponential", "linear", "step")
        half_life_days: Days until relevance drops to 50% (for exponential/linear)
        access_boost: Relevance boost per access (capped at 0.3 total)

    Returns:
        Relevance score between 0.0 and 1.0

    Example:
        >>> from datetime import datetime, timedelta
        >>> now = datetime.now(timezone.utc)
        >>> created = now - timedelta(days=15)
        >>> accessed = now - timedelta(days=2)
        >>> calculate_relevance(created, accessed, access_count=5)
        0.87  # High relevance: recently accessed, frequently used

        >>> old_created = now - timedelta(days=90)
        >>> calculate_relevance(old_created, accessed=None, access_count=0)
        0.125  # Low relevance: old, never accessed
    """
    now = datetime.now(timezone.utc)

    # Ensure created and accessed are timezone-aware
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if accessed and accessed.tzinfo is None:
        accessed = accessed.replace(tzinfo=timezone.utc)

    # Base score starts at 1.0
    score = 1.0

    # Calculate time decay based on last interaction
    # Use last access if available, otherwise creation time
    last_interaction = accessed if accessed else created
    days_since = (now - last_interaction).days

    # Apply decay function
    if decay_function == "exponential":
        # Exponential decay: score = e^(-λt)
        # λ (decay rate) = ln(2) / half_life
        # This gives 50% relevance at half_life days
        decay_rate = 0.693 / half_life_days  # ln(2) ≈ 0.693
        score *= math.exp(-decay_rate * days_since)

    elif decay_function == "linear":
        # Linear decay: score = 1 - (t / max_age)
        # Relevance reaches 0 at 2 × half_life
        max_age_days = half_life_days * 2
        if days_since >= max_age_days:
            score = 0.0
        else:
            score *= 1 - (days_since / max_age_days)

    elif decay_function == "step":
        # Step function: discrete relevance levels
        # 1.0 if fresh, 0.5 if old, 0.1 if ancient
        if days_since < half_life_days:
            score *= 1.0  # Fresh
        elif days_since < half_life_days * 3:
            score *= 0.5  # Old
        else:
            score *= 0.1  # Ancient

    # Apply access frequency boost
    # Each access adds 'access_boost' to relevance, capped at +0.3
    access_boost_total = min(access_boost * access_count, 0.3)
    score = min(score + access_boost_total, 1.0)

    # Round to 3 decimal places
    return round(score, 3)


def recalculate_all_relevance(
    items: list[dict],
    decay_function: DecayFunction = "exponential",
    half_life_days: int = 30,
    access_boost: float = 0.1,
) -> list[dict]:
    """Recalculate relevance scores for a list of items.

    Args:
        items: List of items (tasks/notes) with 'created', 'accessed', 'access_count'
        decay_function: Decay function to use
        half_life_days: Half-life in days
        access_boost: Boost per access

    Returns:
        List of items with updated 'relevance_score' field

    Example:
        >>> tasks = [
        ...     {"id": 1, "created": "2026-01-01T00:00:00Z", "accessed": None, "access_count": 0},
        ...     {"id": 2, "created": "2026-01-20T00:00:00Z", "accessed": "2026-01-24T00:00:00Z", "access_count": 10},
        ... ]
        >>> updated = recalculate_all_relevance(tasks)
        >>> updated[0]["relevance_score"]
        0.347  # Old, never accessed
        >>> updated[1]["relevance_score"]
        1.0  # Recent, frequently accessed
    """
    from idlergear.utils import parse_iso

    updated_items = []

    for item in items:
        # Parse timestamps
        created = parse_iso(item.get("created", ""))
        if not created:
            # Skip items without creation timestamp
            updated_items.append(item)
            continue

        accessed_str = item.get("accessed")
        accessed = parse_iso(accessed_str) if accessed_str else None
        access_count = item.get("access_count", 0)

        # Calculate relevance
        relevance = calculate_relevance(
            created=created,
            accessed=accessed,
            access_count=access_count,
            decay_function=decay_function,
            half_life_days=half_life_days,
            access_boost=access_boost,
        )

        # Update item with new relevance score
        item_copy = item.copy()
        item_copy["relevance_score"] = relevance
        updated_items.append(item_copy)

    return updated_items


def filter_by_relevance(
    items: list[dict],
    min_relevance: float = 0.3,
) -> list[dict]:
    """Filter items by minimum relevance score.

    Args:
        items: List of items with 'relevance_score' field
        min_relevance: Minimum relevance threshold (0.0-1.0)

    Returns:
        Filtered list containing only items with relevance >= min_relevance

    Example:
        >>> items = [
        ...     {"id": 1, "relevance_score": 0.9},
        ...     {"id": 2, "relevance_score": 0.2},
        ...     {"id": 3, "relevance_score": 0.5},
        ... ]
        >>> filter_by_relevance(items, min_relevance=0.3)
        [{"id": 1, "relevance_score": 0.9}, {"id": 3, "relevance_score": 0.5}]
    """
    return [item for item in items if item.get("relevance_score", 1.0) >= min_relevance]


def sort_by_relevance(
    items: list[dict],
    reverse: bool = True,
) -> list[dict]:
    """Sort items by relevance score.

    Args:
        items: List of items with 'relevance_score' field
        reverse: If True, sort descending (highest first). Default: True

    Returns:
        Sorted list

    Example:
        >>> items = [
        ...     {"id": 1, "relevance_score": 0.5},
        ...     {"id": 2, "relevance_score": 0.9},
        ...     {"id": 3, "relevance_score": 0.2},
        ... ]
        >>> sorted_items = sort_by_relevance(items)
        >>> [item["id"] for item in sorted_items]
        [2, 1, 3]
    """
    return sorted(
        items,
        key=lambda item: item.get("relevance_score", 0.0),
        reverse=reverse,
    )


def identify_stale_items(
    items: list[dict],
    stale_threshold: float = 0.2,
) -> list[dict]:
    """Identify stale items (low relevance score).

    Args:
        items: List of items with 'relevance_score' field
        stale_threshold: Relevance below this is considered stale

    Returns:
        List of stale items

    Example:
        >>> items = [
        ...     {"id": 1, "relevance_score": 0.9},
        ...     {"id": 2, "relevance_score": 0.1},
        ...     {"id": 3, "relevance_score": 0.15},
        ... ]
        >>> stale = identify_stale_items(items, stale_threshold=0.2)
        >>> len(stale)
        2
    """
    return [
        item for item in items if item.get("relevance_score", 1.0) < stale_threshold
    ]


def get_relevance_stats(items: list[dict]) -> dict:
    """Calculate statistics about relevance scores.

    Args:
        items: List of items with 'relevance_score' field

    Returns:
        Dict with statistics: count, avg, min, max, stale_count

    Example:
        >>> items = [
        ...     {"id": 1, "relevance_score": 0.9},
        ...     {"id": 2, "relevance_score": 0.5},
        ...     {"id": 3, "relevance_score": 0.1},
        ... ]
        >>> stats = get_relevance_stats(items)
        >>> stats["avg"]
        0.5
        >>> stats["stale_count"]
        1
    """
    if not items:
        return {
            "count": 0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "stale_count": 0,
        }

    scores = [item.get("relevance_score", 0.0) for item in items]

    return {
        "count": len(items),
        "avg": round(sum(scores) / len(scores), 3),
        "min": round(min(scores), 3),
        "max": round(max(scores), 3),
        "stale_count": len([s for s in scores if s < 0.2]),
    }
