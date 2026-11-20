import asyncio
import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)
OrderEvent = dict[str, int | str]


class OrderEventBroker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[
            int,
            list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[OrderEvent]]],
        ] = defaultdict(list)

    async def subscribe(self, order_id: int) -> asyncio.Queue[OrderEvent]:
        queue: asyncio.Queue[OrderEvent] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers[order_id].append((loop, queue))
        return queue

    def unsubscribe(
        self,
        order_id: int,
        queue: asyncio.Queue[OrderEvent],
    ) -> None:
        with self._lock:
            listeners = self._subscribers.get(order_id)
            if listeners is None:
                return
            self._subscribers[order_id] = [
                listener for listener in listeners if listener[1] is not queue
            ]
            if not self._subscribers[order_id]:
                self._subscribers.pop(order_id)

    def publish(self, order_id: int, event: OrderEvent) -> None:
        with self._lock:
            listeners = tuple(self._subscribers.get(order_id, ()))

        for loop, queue in listeners:
            if loop.is_closed():
                continue
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                logger.debug("Skipped an order event for a closed subscriber loop.")


order_event_broker = OrderEventBroker()
