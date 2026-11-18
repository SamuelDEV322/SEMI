"""Same-computer, latest-only IPC. No device is opened here."""

from contextlib import contextmanager
import os
import socket


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
