from __future__ import annotations

import logging
import subprocess  # noqa: S404
import time
from typing import TYPE_CHECKING, Any

from wskr.core.errors import CommandRunnerError

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)


class CommandRunner:
    """Thin wrapper around :mod:`subprocess` with sensible defaults.

    Provides retry and timeout handling for subprocess invocations.
    """

    def __init__(self, *, timeout: float = 1.0, retries: int = 0, retry_delay: float = 0.0) -> None:
        self._timeout = timeout
        self._retries = retries
        self._retry_delay = retry_delay

    @property
    def timeout(self) -> float:
        """Default timeout in seconds."""
        return self._timeout

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
        for attempt in range(attempts):
            try:
                logger.debug(
                    "CommandRunner.run: cmd=%s attempt=%d/%d timeout=%s",
                    cmd,
                    attempt + 1,
                    attempts,
                    effective_timeout,
                )
                return subprocess.run(  # noqa: S603,PLW1510
                    cmd,
                    timeout=effective_timeout,
                    **kwargs,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.debug("CommandRunner.run failed: %s", e, exc_info=True)
                if attempt == attempts - 1:
                    msg = f"command {cmd!r} failed"
                    raise CommandRunnerError(msg) from e
                if self._retry_delay:
                    time.sleep(self._retry_delay)

        msg = "unreachable"
        raise CommandRunnerError(msg)

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
