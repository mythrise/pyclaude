"""Buddy exports."""

from .animations import SPRITE_FRAMES
from .notifications import Notification, NotificationQueue
from .states import BuddyState, BuddyStateMachine

try:
    from .widget import BuddyWidget
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    BuddyWidget = None

__all__ = [
    "BuddyState",
    "BuddyStateMachine",
    "BuddyWidget",
    "Notification",
    "NotificationQueue",
    "SPRITE_FRAMES",
]
