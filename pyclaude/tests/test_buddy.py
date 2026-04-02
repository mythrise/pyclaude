import asyncio

from pyclaude.buddy import BuddyState, BuddyStateMachine, Notification, NotificationQueue


def test_buddy_state_machine() -> None:
    machine = BuddyStateMachine()
    assert machine.on_thinking_start() == BuddyState.THINKING
    assert machine.on_thinking_done() == BuddyState.HAPPY
    machine.tick()
    machine.tick()
    assert machine.current == BuddyState.IDLE


def test_notification_queue() -> None:
    queue = NotificationQueue()
    asyncio.run(queue.push(Notification(text="hello")))
    item = asyncio.run(queue.next())
    assert item.text == "hello"
