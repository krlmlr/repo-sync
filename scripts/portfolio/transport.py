"""The one place a request leaves this machine.

`urllib.request` from the standard library rather than a dependency: the collector makes plain
JSON POSTs and GETs with a bearer token, which is what `urlopen` does, and a portfolio reading is
not worth a package to install, pin and update.

Every request goes through a `Transport` so that the collectors can be exercised without a network:
the tests hand them a transport that answers from recorded fixtures, and nothing above this file
knows the difference.

Requests are serialised rather than fanned out. The documented hourly limit is not the one that
bites -- secondary limits react to concurrency, and answer with a 403 that costs the whole run --
so this is the one tool here that does not use `parallel`.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


class Unreadable(Exception):
    """A source that could not be read, for a reason worth showing next to the package it belongs to."""


class RateLimited(Unreadable):
    """The remote asking to be left alone for a while, which is a wait rather than a failure."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Transport:
    """A request, and nothing else: no retries, no counting, no interpretation."""

    def request(self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None) -> Response:
        raise NotImplementedError


class UrllibTransport(Transport):
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def request(self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None) -> Response:
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return Response(response.status, dict(response.headers), response.read())
        except urllib.error.HTTPError as exc:
            # An HTTP error is an answer, not a broken connection: a 403 carrying a rate-limit
            # header is a wait, and a 404 is a fact about the repository. Both are read above.
            return Response(exc.code, dict(exc.headers or {}), exc.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise Unreadable(f"{method} {url}: {exc}") from exc


@dataclass
class Client:
    """A transport with the three things every caller of one here wants: counting, backoff, and JSON.

    The count is reported at the end of a run the way `report_failures` reports failures: a budget
    that is only noticed when it is spent is a budget nobody is managing.
    """

    transport: Transport
    attempts: int = 4
    sleep: Callable[[float], None] = time.sleep
    counts: dict[str, int] = field(default_factory=dict)

    def request(
        self,
        method: str,
        url: str,
        *,
        kind: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> Response:
        delay = 2.0
        last: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            self.counts[kind] = self.counts.get(kind, 0) + 1
            try:
                response = self.transport.request(method, url, headers=headers, body=body)
            except Unreadable as exc:
                last = exc
                if attempt == self.attempts:
                    raise
                self.sleep(delay)
                delay *= 2
                continue
            limited = rate_limit_wait(response)
            if limited is None:
                return response
            last = RateLimited(f"{method} {url}: rate limited", limited)
            if attempt == self.attempts:
                break
            # The remote's own figure when it gives one, ours when it does not.
            self.sleep(min(limited, 60.0) if limited else delay)
            delay *= 2
        raise last if last else Unreadable(f"{method} {url}: no attempt succeeded")

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def rate_limit_wait(response: Response) -> float | None:
    """How long the remote wants us to wait, or None when it is not asking.

    GitHub says so three ways -- `Retry-After`, an exhausted `x-ratelimit-remaining` on a 403, and
    a secondary-limit message in the body -- and a collector that only reads the first of them
    retries straight into the next refusal.
    """
    if response.status not in (403, 429):
        return None
    headers = {key.lower(): value for key, value in response.headers.items()}
    retry_after = headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            return 60.0
    if headers.get("x-ratelimit-remaining") == "0":
        return 60.0
    body = response.body.decode("utf-8", errors="replace").lower()
    if "rate limit" in body or "secondary rate" in body or "abuse" in body:
        return 60.0
    return None
