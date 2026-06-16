import typing
import inspect


class Reporter:
    """Minimal reporting interface for status/progress callbacks."""

    def status(self, message: str) -> None:
        raise NotImplementedError

    def progress(self, current: int, total: int, message: typing.Optional[str] = None) -> None:
        raise NotImplementedError

    def match_finalized(self, match_id: str, match: typing.Optional[dict] = None) -> None:
        """Called when a match's data has been saved/finalized.

        Args:
            match_id: The unique identifier of the finalized match.
            match: Optional dict representation of the finalized match data.
                When provided, enables streaming use cases (e.g. pushing
                the match to the prediction engine immediately). May be
                None for backward compatibility or when only the id is
                relevant (e.g. timing instrumentation).
        """
        raise NotImplementedError


def _callback_accepts_match(cb: typing.Callable) -> bool:
    """Detect whether a match_finalized callback accepts a second 'match' arg.

    Allows backward compatibility: callbacks written as ``def cb(match_id)``
    keep working, while new callbacks can opt into receiving the match dict
    via ``def cb(match_id, match=None)`` or ``def cb(match_id, match)``.
    """
    try:
        sig = inspect.signature(cb)
        params = list(sig.parameters.values())
        # Callbacks with 2+ parameters accept the match arg
        if len(params) >= 2:
            return True
        # Callbacks with *args or **kwargs accept it too
        if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params):
            return True
        return False
    except (ValueError, TypeError):
        return False


class CallbackReporter(Reporter):
    """Reporter that forwards to provided callables if available, with CLI fallback to print()."""

    def __init__(
        self,
        status_callback: typing.Optional[typing.Callable[[str], None]] = None,
        progress_callback: typing.Optional[typing.Callable[[int, int, typing.Optional[str]], None]] = None,
        match_finalized_callback: typing.Optional[typing.Callable] = None,
    ) -> None:
        self._status_cb = status_callback
        self._progress_cb = progress_callback
        self._match_finalized_cb = match_finalized_callback
        # Detect arity once to avoid repeated introspection
        self._match_cb_accepts_match = (
            _callback_accepts_match(match_finalized_callback)
            if match_finalized_callback is not None
            else False
        )

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

    def match_finalized(self, match_id: str, match: typing.Optional[dict] = None) -> None:
        cb = self._match_finalized_cb
        if cb is not None:
            try:
                # Forward the match dict only if the callback declares it
                if self._match_cb_accepts_match:
                    cb(match_id, match)
                else:
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


