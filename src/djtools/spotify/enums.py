"""Enumerations for the spotify package.

This module contains enum types used by the spotify config and helpers
to avoid cyclic imports.
"""

from enum import Enum

import yaml


class SubredditPeriod(Enum):
    """Time period for subreddit queries."""

    ALL = "all"
    DAY = "day"
    HOUR = "hour"
    MONTH = "month"
    WEEK = "week"
    YEAR = "year"


def subreddit_period_representer(dumper, data):
    """YAML representer for SubredditPeriod."""
    return dumper.represent_scalar("!SubredditPeriod", data.value)


def subreddit_period_constructor(loader, node):
    """YAML constructor for SubredditPeriod."""
    return SubredditPeriod(loader.construct_scalar(node))


yaml.add_representer(SubredditPeriod, subreddit_period_representer)
yaml.add_constructor("!SubredditPeriod", subreddit_period_constructor)


class SubredditType(Enum):
    """Type of subreddit sort."""

    CONTROVERSIAL = "controversial"
    HOT = "hot"
    NEW = "new"
    RISING = "rising"
    TOP = "top"


def subreddit_type_representer(dumper, data):
    """YAML representer for SubredditType."""
    return dumper.represent_scalar("!SubredditType", data.value)


def subreddit_type_constructor(loader, node):
    """YAML constructor for SubredditType."""
    return SubredditType(loader.construct_scalar(node))


yaml.add_representer(SubredditType, subreddit_type_representer)
yaml.add_constructor("!SubredditType", subreddit_type_constructor)
