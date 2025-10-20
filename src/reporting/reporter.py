import typing


class Reporter:
    """Minimal reporting interface for status/progress callbacks."""

    def status(self, message: str) -> None:
        raise NotImplementedError

    def progress(self, current: int, total: int, message: typing.Optional[str] = None) -> None:
        raise NotImplementedError

    def match_finalized(self, match_id: str) -> None:
        """Called when a match's data has been saved/finalized."""
        raise NotImplementedError


class CallbackReporter(Reporter):
    """Reporter that forwards to provided callables if available, with CLI fallback to print()."""

    def __init__(
        self,
        status_callback: typing.Optional[typing.Callable[[str], None]] = None,
        progress_callback: typing.Optional[typing.Callable[[int, int, typing.Optional[str]], None]] = None,
        match_finalized_callback: typing.Optional[typing.Callable[[str], None]] = None,
    ) -> None:
        self._status_cb = status_callback
        self._progress_cb = progress_callback
        self._match_finalized_cb = match_finalized_callback

    def status(self, message: str) -> None:
        cb = self._status_cb
        if cb is not None:
            try:
                cb(message)
            except Exception:
                # Fallback to print for CLI when callback fails
                try:
                    print(message)
                except Exception:
                    pass
        else:
            # Fallback to print for CLI when no callback provided
            try:
                print(message)
            except Exception:
                pass

    def progress(self, current: int, total: int, message: typing.Optional[str] = None) -> None:
        cb = self._progress_cb
        if cb is not None:
            try:
                cb(current, total, message)
            except Exception:
                # Fallback to print for CLI when callback fails
                try:
                    progress_msg = f"Progress: {current}/{total}"
                    if message:
                        progress_msg += f" - {message}"
                    print(progress_msg)
                except Exception:
                    pass
        else:
            # Fallback to print for CLI when no callback provided
            try:
                progress_msg = f"Progress: {current}/{total}"
                if message:
                    progress_msg += f" - {message}"
                print(progress_msg)
            except Exception:
                pass

    def match_finalized(self, match_id: str) -> None:
        cb = self._match_finalized_cb
        if cb is not None:
            try:
                cb(match_id)
            except Exception:
                pass
        # No CLI print fallback; this is a structured event


class NullReporter(Reporter):
    """No-op reporter for tests or silent runs."""

    def status(self, message: str) -> None:
        return None

    def progress(self, current: int, total: int, message: typing.Optional[str] = None) -> None:
        return None


class CaptureReporter(Reporter):
    """Captures status/progress messages in-memory for assertions."""

    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.progresses: list[tuple[int, int, typing.Optional[str]]] = []

    def status(self, message: str) -> None:
        self.statuses.append(str(message))

    def progress(self, current: int, total: int, message: typing.Optional[str] = None) -> None:
        self.progresses.append((int(current), int(total), message))


