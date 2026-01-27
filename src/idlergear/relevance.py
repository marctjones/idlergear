"""Relevance scoring and memory decay for knowledge management.

Implements time-based decay functions to automatically reduce the relevance
of old, unaccessed knowledge items while boosting frequently accessed items.
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
    """Calculate relevance score (0.0-1.0) based on temporal and access patterns.

    Args:
        created: When the item was created
        accessed: When the item was last accessed (None if never accessed)
        access_count: Number of times the item has been accessed
        decay_function: Type of decay curve to use
        half_life_days: Days until relevance drops to 50% (for exponential decay)
        access_boost: Boost per access (capped at 0.3 total)

    Returns:
        Relevance score from 0.0 (irrelevant) to 1.0 (highly relevant)

    Examples:
        >>> from datetime import timedelta
        >>> now = datetime.now(timezone.utc)
        >>> created = now - timedelta(days=30)
        >>> # Item created 30 days ago, never accessed
        >>> calculate_relevance(created)
        0.5
        >>> # Item created 30 days ago, accessed 5 times recently
        >>> accessed = now - timedelta(days=1)
        >>> calculate_relevance(created, accessed, access_count=5)
        0.8
    """
    now = datetime.now(timezone.utc)

    # Ensure created is timezone-aware
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    # Base score starts at 1.0
    score = 1.0

    # Time decay based on last access (or creation if never accessed)
    last_interaction = accessed or created
    if last_interaction.tzinfo is None:
        last_interaction = last_interaction.replace(tzinfo=timezone.utc)

    days_since = (now - last_interaction).total_seconds() / 86400  # Convert to days

    if decay_function == "exponential":
        # Exponential decay: score = e^(-λt) where λ = ln(2) / half_life
        decay_rate = math.log(2) / half_life_days
        score *= math.exp(-decay_rate * days_since)

    elif decay_function == "linear":
        # Linear decay: score = 1 - (t / max_age)
        max_age_days = half_life_days * 2
        score *= max(0.0, 1.0 - (days_since / max_age_days))

    elif decay_function == "step":
        # Step function: discrete relevance levels
        if days_since < half_life_days:
            score *= 1.0  # Fresh
        elif days_since < half_life_days * 3:
            score *= 0.5  # Old
        else:
            score *= 0.1  # Ancient

    # Boost for frequent access (cap at +0.3)
    access_boost_total = min(access_boost * access_count, 0.3)
    score = min(score + access_boost_total, 1.0)

    return round(score, 3)


def calculate_all_relevance(
    items: list[dict],
    decay_function: DecayFunction = "exponential",
    half_life_days: int = 30,
    access_boost: float = 0.1,
) -> list[dict]:
    """Calculate relevance scores for a list of items.

    Adds or updates 'relevance_score' field in each item.

    Args:
        items: List of items with 'created', optionally 'accessed' and 'access_count'
        decay_function: Type of decay curve
        half_life_days: Days until 50% relevance
        access_boost: Boost per access

    Returns:
        Same list with updated relevance_score fields
    """
    for item in items:
        created_str = item.get("created")
        accessed_str = item.get("accessed")

        if not created_str:
            # No created timestamp, assign default low relevance
            item["relevance_score"] = 0.5
            continue

        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        accessed = (
            datetime.fromisoformat(accessed_str.replace("Z", "+00:00"))
            if accessed_str
            else None
        )
        access_count = item.get("access_count", 0)

        item["relevance_score"] = calculate_relevance(
            created=created,
            accessed=accessed,
            access_count=access_count,
            decay_function=decay_function,
            half_life_days=half_life_days,
            access_boost=access_boost,
        )

    return items


def filter_by_relevance(
    items: list[dict], min_relevance: float = 0.3, limit: int | None = None
) -> list[dict]:
    """Filter items by minimum relevance and optionally limit results.

    Args:
        items: List of items with 'relevance_score' field
        min_relevance: Minimum relevance threshold (0.0-1.0)
        limit: Maximum number of items to return (None = no limit)

    Returns:
        Filtered and sorted list (highest relevance first)
    """
    # Filter by minimum relevance
    filtered = [
        item for item in items if item.get("relevance_score", 0.0) >= min_relevance
    ]

    # Sort by relevance (highest first)
    filtered.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    # Apply limit if specified
    if limit is not None:
        filtered = filtered[:limit]

    return filtered


def get_stale_items(items: list[dict], threshold: float = 0.2) -> list[dict]:
    """Get items with relevance below threshold (candidates for archiving).

    Args:
        items: List of items with 'relevance_score' field
        threshold: Relevance threshold for considering item stale

    Returns:
        List of stale items sorted by relevance (lowest first)
    """
    stale = [item for item in items if item.get("relevance_score", 1.0) < threshold]
    stale.sort(key=lambda x: x.get("relevance_score", 0.0))
    return stale


def sort_by_relevance(items: list[dict], reverse: bool = True) -> list[dict]:
    """Sort items by relevance score.

    Args:
        items: List of items with 'relevance_score' field
        reverse: If True, sort highest to lowest (default). If False, lowest to highest.

    Returns:
        Sorted list (modifies in-place and returns)
    """
    items.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=reverse)
    return items
