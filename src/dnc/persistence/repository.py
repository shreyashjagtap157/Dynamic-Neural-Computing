"""Deterministic event repository with OCC and transactional outbox/inbox."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dnc.persistence.contracts import DurableEvent, OutboxMessage


@dataclass
class EventRepository:
    _events: dict[tuple[str, str], list[DurableEvent]] = field(default_factory=dict)
    _outbox: dict[tuple[str, str], OutboxMessage] = field(default_factory=dict)
    _inbox: dict[tuple[str, str], str] = field(default_factory=dict)

    def append(
        self,
        event: DurableEvent,
        *,
        expected_version: int,
        outbox: tuple[OutboxMessage, ...] = (),
    ) -> None:
        key = (event.tenant_id, event.aggregate_id)
        events = self._events.setdefault(key, [])
        current = events[-1].aggregate_version if events else 0
        if current != expected_version or event.aggregate_version != current + 1:
            raise ValueError("optimistic concurrency conflict")
        if any(
            item.event_id == event.event_id and item.tenant_id == event.tenant_id
            for values in self._events.values() for item in values
        ):
            raise ValueError("duplicate durable event")
        message_ids = [message.message_id for message in outbox]
        if len(message_ids) != len(set(message_ids)) or any(
            (event.tenant_id, message_id) in self._outbox for message_id in message_ids
        ):
            raise ValueError("duplicate outbox message")
        if any(message.tenant_id != event.tenant_id for message in outbox):
            raise ValueError("outbox tenant MUST match event tenant")
        events.append(event)
        for message in outbox:
            self._outbox[(message.tenant_id, message.message_id)] = message

    def load(self, aggregate_id: str, *, tenant_id: str) -> tuple[DurableEvent, ...]:
        return tuple(self._events.get((tenant_id, aggregate_id), ()))

    def pending_outbox(self, *, tenant_id: str) -> tuple[OutboxMessage, ...]:
        return tuple(
            self._outbox[key] for key in sorted(self._outbox)
            if self._outbox[key].tenant_id == tenant_id and not self._outbox[key].published
        )

    def mark_published(self, message_id: str, *, tenant_id: str) -> None:
        key = (tenant_id, message_id)
        message = self._outbox.get(key)
        if message is None:
            raise KeyError("unknown tenant-scoped outbox message")
        self._outbox[key] = replace(message, published=True)

    def receive_once(self, message: OutboxMessage, result_fingerprint: str) -> bool:
        key = (message.tenant_id, message.idempotency_key)
        previous = self._inbox.get(key)
        if previous is None:
            self._inbox[key] = result_fingerprint
            return True
        if previous != result_fingerprint:
            raise ValueError("idempotency key reused with conflicting result")
        return False

    def rebuild(self, aggregate_id: str, *, tenant_id: str, reducer, initial):
        state = initial
        for event in self.load(aggregate_id, tenant_id=tenant_id):
            state = reducer(state, event)
        return state

    def snapshot(self):
        return (
            {key: tuple(values) for key, values in self._events.items()},
            dict(self._outbox),
            dict(self._inbox),
        )

    def restore(self, state) -> None:
        events, outbox, inbox = state
        self._events = {key: list(values) for key, values in events.items()}
        self._outbox = dict(outbox)
        self._inbox = dict(inbox)
