import asyncio

from crypto_analyzer.core.config import (
    BINANCE_MAX_CONCURRENT_REQUESTS,
    OKX_MAX_CONCURRENT_REQUESTS,
    BINANCE_MIN_REQUEST_INTERVAL,
    OKX_MIN_REQUEST_INTERVAL,
)


class AsyncConcurrencyLimiter:
    def __init__(self, max_concurrent: int, min_interval: float = 0.0) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        if min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        self._sem = asyncio.Semaphore(max_concurrent)
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_acquire = 0.0

    async def __aenter__(self):
        await self._sem.acquire()
        if self._min_interval <= 0:
            return self

        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            elapsed = now - self._last_acquire
            wait_for = self._min_interval - elapsed
            if wait_for > 0:
                await asyncio.sleep(wait_for)
                now = loop.time()
            self._last_acquire = now

        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._sem.release()
        return False


binance_public_limiter = AsyncConcurrencyLimiter(
    BINANCE_MAX_CONCURRENT_REQUESTS,
    BINANCE_MIN_REQUEST_INTERVAL,
)
okx_public_limiter = AsyncConcurrencyLimiter(
    OKX_MAX_CONCURRENT_REQUESTS,
    OKX_MIN_REQUEST_INTERVAL,
)
