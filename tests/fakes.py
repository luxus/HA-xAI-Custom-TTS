"""Shared HTTP fakes for SpaceXAI unit tests."""

from __future__ import annotations


class FakeResponse:
    def __init__(self, status: int, body: object) -> None:
        self.status = status
        self._body = body

    async def json(self) -> object:
        if isinstance(self._body, (dict, list)):
            return self._body
        raise ValueError("not json")

    async def text(self) -> str:
        return str(self._body)

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def __init__(self, script: list[tuple[str, int, object]]) -> None:
        self.script = list(script)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        payload = dict(data or {})
        self.calls.append((url, payload))
        expected_url, status, body = self.script.pop(0)
        assert url == expected_url
        return FakeResponse(status, body)


class FakeHttpxResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
        self.content = b""

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpxClient:
    def __init__(
        self,
        response: FakeHttpxResponse | None = None,
        *,
        expected_url: str | None = None,
        responses: list[FakeHttpxResponse] | None = None,
    ) -> None:
        if responses is not None:
            self._queue = list(responses)
        elif response is not None:
            self._queue = [response]
        else:
            self._queue = []
        self.response = self._queue[0] if self._queue else FakeHttpxResponse(200, {})
        self.expected_url = expected_url
        self.calls: list[dict[str, object]] = []

    def _next(self, url: str) -> FakeHttpxResponse:
        if self.expected_url is not None:
            assert url == self.expected_url
        if self._queue:
            item = self._queue.pop(0)
            self.response = item
            return item
        return self.response

    async def post(self, url: str, **kwargs: object) -> FakeHttpxResponse:
        self.calls.append({"method": "post", "url": url, **kwargs})
        return self._next(url)

    async def get(self, url: str, **kwargs: object) -> FakeHttpxResponse:
        self.calls.append({"method": "get", "url": url, **kwargs})
        return self._next(url)
