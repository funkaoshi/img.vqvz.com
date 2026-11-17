"""A TTL cache in front of FlickrClient.

Every page view used to hit Flickr live (and Rack::Cache never stored anything
because no Cache-Control was sent). Caching here keeps the site fast even
without a proxy in front, and the HTTP cache headers in site.py help when there
is one.
"""

from __future__ import annotations

import threading
from typing import Any

from cachetools import TTLCache

from .flickr import FlickrClient


class CachedFlickr:
    """Wraps a FlickrClient; method results are cached by (name, args)."""

    # User lookups change approximately never.
    LONG_LIVED = {"user"}

    def __init__(self, client: FlickrClient, ttl: int = 300, long_ttl: int = 86400, maxsize: int = 512):
        self.client = client
        self._short = TTLCache(maxsize=maxsize, ttl=ttl)
        self._long = TTLCache(maxsize=64, ttl=long_ttl)
        self._lock = threading.Lock()

    def __getattr__(self, name: str) -> Any:
        fn = getattr(self.client, name)
        if not callable(fn) or name.startswith("_") or name == "call":
            return fn
        store = self._long if name in self.LONG_LIVED else self._short

        def cached(*args: Any, **kwargs: Any) -> Any:
            key = (name, args, tuple(sorted(kwargs.items())))
            with self._lock:
                if key in store:
                    return store[key]
            value = fn(*args, **kwargs)  # errors propagate and are not cached
            with self._lock:
                store[key] = value
            return value

        return cached

    def clear(self) -> None:
        with self._lock:
            self._short.clear()
            self._long.clear()
