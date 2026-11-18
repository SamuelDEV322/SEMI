"""Same-computer, latest-only IPC. No device is opened here."""

from contextlib import contextmanager
import os
import socket
import json
import stat
import tempfile
import time
import logging


class PublicationError(RuntimeError):
    """No new frame was published; callers must not publish this error again."""


def publish_atomic(path, value):
    """Closed, unique, same-directory temporary; at most 150 ms retry backoff.

    Caller owns reader_lock throughout acquisition. Only Windows access/sharing
    violations are candidates for brief retry; ReadOnly is never repaired here.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf8",
            dir=path.parent,
            prefix=f".{path.name}.{os.getpid()}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            from pathlib import Path

            temporary = Path(output.name)
            json.dump(value, output, allow_nan=False)
        # Context exit closes the handle before the very first rename attempt.
        for attempt, delay in enumerate((0.01, 0.02, 0.04, 0.08, None), start=1):
            try:
                attributes = getattr(path.stat(), "st_file_attributes", 0)
            except FileNotFoundError:
                attributes = 0
            if attributes & stat.FILE_ATTRIBUTE_READONLY:
                raise PermissionError("Destination has Windows ReadOnly attribute")
            try:
                os.replace(temporary, path)
                return
            except OSError as error:
                if getattr(error, "winerror", None) not in (5, 32, 33) or delay is None:
                    error.add_note(f"atomic replace attempts: {attempt}")
                    raise
                time.sleep(delay)
    except (OSError, ValueError, TypeError) as error:
        raise PublicationError(
            f"LiDAR publication failed for {path}: {error}. No new frame published; "
            "previous JSON preserved. Check ReadOnly, directory/file ACL and open "
            "handles (delete sharing). No USB/protocol failure inferred."
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                logging.getLogger(__name__).warning(
                    "Cannot remove own LiDAR temporary %s: %s", temporary, error
                )


def local_host():
    return socket.gethostname().casefold()


@contextmanager
def reader_lock(path):
    """One publisher per spool, including independent Django command processes.

    The OS releases this lock after a crash. The serial driver also needs exclusive
    ownership of the selected port; this lock cannot arbitrate RoboStudio.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.with_suffix(".lock").open("a+b")
    acquired = False
    try:
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as error:
            raise RuntimeError("Another SEMI reader owns this scan channel") from error
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
