import heapq
import itertools
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import Future
from typing import Any


class TaskQueue:
    """Bounds concurrency and rate for Agent invocations, with retry/backoff on
    failure and priority scheduling: higher `priority` tasks are dispatched to
    a free worker before lower-priority ones (FIFO among equal priorities).

    Backed by a fixed pool of worker threads pulling from a priority heap,
    rather than ThreadPoolExecutor's plain FIFO queue — that's the only way to
    get real priority ordering under a bounded pool.
    """

    def __init__(
        self,
        max_concurrency: int = 1,
        rate_limit_per_sec: float | None = None,
        max_retries: int = 0,
        backoff_base_sec: float = 1.0,
    ):
        self.max_concurrency = max_concurrency
        self.rate_limit_per_sec = rate_limit_per_sec
        self.max_retries = max_retries
        self.backoff_base_sec = backoff_base_sec

        self._heap: list[tuple[int, int, Callable, tuple, dict, Future]] = []
        self._counter = itertools.count()
        self._cv = threading.Condition()
        self._shutdown = False

        self._rate_lock = threading.Lock()
        self._last_submit_at = 0.0

        self._workers = [
            threading.Thread(target=self._worker_loop, daemon=True) for _ in range(max_concurrency)
        ]
        for worker in self._workers:
            worker.start()

    def submit(self, fn: Callable[..., Any], *args: Any, priority: int = 0, **kwargs: Any) -> Future:
        future: Future = Future()
        with self._cv:
            heapq.heappush(self._heap, (-priority, next(self._counter), fn, args, kwargs, future))
            self._cv.notify()
        return future

    def map(
        self,
        fn: Callable[[Any], Any],
        items: Iterable[Any],
        *,
        priority_key: Callable[[Any], int] | None = None,
    ) -> list[Any]:
        futures = [
            self.submit(fn, item, priority=priority_key(item) if priority_key else 0) for item in items
        ]
        return [future.result() for future in futures]

    def shutdown(self, wait: bool = True) -> None:
        with self._cv:
            self._shutdown = True
            self._cv.notify_all()
        if wait:
            for worker in self._workers:
                worker.join()

    def _worker_loop(self) -> None:
        while True:
            with self._cv:
                while not self._heap and not self._shutdown:
                    self._cv.wait()
                if not self._heap and self._shutdown:
                    return
                _, _, fn, args, kwargs, future = heapq.heappop(self._heap)

            if not future.set_running_or_notify_cancel():
                continue

            self._throttle()
            try:
                result = self._run_with_retry(fn, args, kwargs)
            except BaseException as exc:  # noqa: BLE001 — must reach the Future, not kill the worker
                future.set_exception(exc)
            else:
                future.set_result(result)

    def _throttle(self) -> None:
        if self.rate_limit_per_sec is None:
            return
        min_interval = 1.0 / self.rate_limit_per_sec
        with self._rate_lock:
            wait = self._last_submit_at + min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_submit_at = time.monotonic()

    def _run_with_retry(self, fn: Callable[..., Any], args: tuple, kwargs: dict) -> Any:
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.backoff_base_sec * (2**attempt))
                attempt += 1
