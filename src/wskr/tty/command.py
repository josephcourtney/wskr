from __future__ import annotations

import subprocess  # noqa: S404
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


class CommandRunner:
    """Thin wrapper around :mod:`subprocess` with sensible defaults.

    Provides retry and timeout handling for subprocess invocations.
    """

    def __init__(self, *, timeout: float = 1.0, retries: int = 0, retry_delay: float = 0.0) -> None:
        self._timeout = timeout
        self._retries = retries
        self._retry_delay = retry_delay

    def run(
        self,
        cmd: Sequence[str],
        *,
        timeout: float | None = None,
        retries: int | None = None,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[Any]:
        """Run *cmd* returning the :class:`~subprocess.CompletedProcess`.

        ``timeout`` and ``retries`` default to the values provided at
        construction time.  Retries are attempted on
        ``CalledProcessError`` and ``TimeoutExpired``.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        attempts = (retries if retries is not None else self._retries) + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return subprocess.run(  # noqa: S603,PLW1510
                    cmd,
                    timeout=effective_timeout,
                    **kwargs,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                last_exc = e
                if attempt == attempts - 1:
                    raise
                if self._retry_delay:
                    time.sleep(self._retry_delay)
        if last_exc is None:  # pragma: no cover
            msg = "unreachable"
            raise RuntimeError(msg)
        raise last_exc

    def check_output(
        self,
        cmd: Sequence[str],
        *,
        timeout: float | None = None,
        retries: int | None = None,
        **kwargs: Any,
    ) -> str | bytes:
        """Return the standard output of *cmd*.

        Equivalent to :func:`subprocess.check_output` but honours default
        timeouts and retry logic.
        """
        proc = self.run(
            cmd,
            timeout=timeout,
            retries=retries,
            capture_output=True,
            check=True,
            **kwargs,
        )
        return proc.stdout
