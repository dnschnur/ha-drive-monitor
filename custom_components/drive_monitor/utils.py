"""Common utility functions shared across the component."""

from __future__ import annotations

import asyncio
import time

from functools import wraps


def async_cache(ttl: int | None = None):
  """Decorator similar to functools.cache, but supporting async functions.

  An async coroutine object can only be awaited once, making it impossible to
  use the standard @cache decorator on an async function.

  When decorated with @async_cache, the function will return a new coroutine
  each time it is called. Internally, these use a cached Task created from the
  original function. As with a normal coroutine, the original function is only
  called and scheduled when the decorated function is called and awaited.

  If a TTL is specified, and the age of the cached Task passes the expiration,
  then the next time the decorated function is called, it will replace the Task
  with a new one, calling and scheduling the original function again.

  Arguments are equal by value, ignoring type. So an @async_cache function that
  is called twice, with args of different types but having the same value, will
  treat the second call as cached.

  Args:
    ttl: Number of seconds that cache entries are valid for.
        Note: Stale entries are not removed from the cache; they are simply
        replaced the next time the function is called and awaited.
  """
  calls = {}
  def decorator(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
      key = hash((args, frozenset(kwargs.items())))
      task, timestamp = calls.get(key, (None, None))
      if not task or ttl and time.time_ns() - timestamp > ttl * 1e9:
        task = asyncio.ensure_future(f(*args, **kwargs))
        calls[key] = (task, time.time_ns() if ttl else None)
      return await task
    return wrapper
  return decorator
