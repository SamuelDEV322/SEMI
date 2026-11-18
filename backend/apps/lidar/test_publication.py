"""Local file contention only. No serial factory, device or user file is opened."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import ctypes
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
from unittest import skipUnless
from unittest.mock import Mock, patch
from django.core.management import CommandError
from django.test import SimpleTestCase
from adapters.lidar_ipc import publish_atomic, PublicationError, reader_lock
from apps.agriculture.management.commands.lidar_usb import Command


@contextmanager
def deny_delete(path, exclusive=False):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.CreateFileW(
        str(path), 0x80000000, 0 if exclusive else 3, None, 3, 0, None
    )
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


class PublicationTests(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "latest.json"
        self.path.write_text('{"old": true}', encoding="utf8")
        self.original = self.path.read_bytes()

    def winerror(self, code):
        error = PermissionError("fixture access failure")
        error.winerror = code
        return error

    def test_transient_errors_retry_closed_same_directory_temporary(self):
        original = os.replace
        sources = []
        for code in [5, 32, 33]:

            def replace(source, target):
                sources.append(source)
                self.assertEqual(source.parent, self.path.parent)
                if os.name == "nt":
                    with deny_delete(source, exclusive=True):
                        pass
                self.assertEqual(json.loads(source.read_text()), {"new": code})
                if len(sources) % 2:
                    raise self.winerror(code)
                original(source, target)

            with patch(
                "adapters.lidar_ipc.os.replace", side_effect=replace
            ) as call, patch("adapters.lidar_ipc.time.sleep") as sleep:
                publish_atomic(self.path, {"new": code})
                self.assertEqual(call.call_count, 2)
                sleep.assert_called_once_with(0.01)
        self.assertEqual(len(set(sources)), 3)

    def test_permanent_access_failure_preserves_json_and_is_bounded(self):
        with patch(
            "adapters.lidar_ipc.os.replace", side_effect=self.winerror(5)
        ) as replace, patch("adapters.lidar_ipc.time.sleep") as sleep:
            with self.assertRaisesRegex(PublicationError, "No new frame published"):
                publish_atomic(self.path, {"new": True})
            self.assertEqual(replace.call_count, 5)
            self.assertEqual(
                [c.args[0] for c in sleep.call_args_list], [0.01, 0.02, 0.04, 0.08]
            )
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_other_io_errors_and_bad_json_do_not_retry(self):
        with patch(
            "adapters.lidar_ipc.os.replace", side_effect=OSError(28, "full")
        ) as replace, patch("adapters.lidar_ipc.time.sleep") as sleep:
            with self.assertRaises(PublicationError):
                publish_atomic(self.path, {})
            replace.assert_called_once()
            sleep.assert_not_called()
        with patch("adapters.lidar_ipc.os.replace") as replace:
            with self.assertRaises(PublicationError):
                publish_atomic(self.path, {"bad": float("nan")})
            replace.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.original)

    @skipUnless(os.name == "nt", "Native Windows attribute/handle behavior")
    def test_readonly_fails_immediately_without_changing_attribute(self):
        os.chmod(self.path, stat.S_IREAD)  # Only this test's disposable file.
        try:
            with patch("adapters.lidar_ipc.os.replace") as replace:
                with self.assertRaisesRegex(PublicationError, "ReadOnly"):
                    publish_atomic(self.path, {})
                replace.assert_not_called()
            self.assertTrue(
                self.path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
            )
        finally:
            os.chmod(self.path, stat.S_IWRITE | stat.S_IREAD)

    @skipUnless(os.name == "nt", "Native Windows sharing contention")
    def test_native_open_handle_release_allows_retry(self):
        held = deny_delete(self.path)
        held.__enter__()
        released = False

        def release(_):
            nonlocal released
            held.__exit__(None, None, None)
            released = True

        try:
            with patch("adapters.lidar_ipc.time.sleep", side_effect=release) as sleep:
                publish_atomic(self.path, {"after_release": True})
                sleep.assert_called_once()
        finally:
            if not released:
                held.__exit__(None, None, None)
        self.assertEqual(json.loads(self.path.read_text()), {"after_release": True})

    @skipUnless(os.name == "nt", "Native Windows sharing contention")
    def test_native_permanent_open_handle_preserves_last_frame(self):
        with deny_delete(self.path), patch("adapters.lidar_ipc.time.sleep") as sleep:
            with self.assertRaises(PublicationError):
                publish_atomic(self.path, {})
            self.assertEqual(sleep.call_count, 4)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_concurrent_writers_cannot_share_publisher_lock(self):
        with reader_lock(self.path), ThreadPoolExecutor(max_workers=1) as pool:

            def second():
                with reader_lock(self.path):
                    self.fail("Second publisher entered")

            with self.assertRaises(RuntimeError):
                pool.submit(second).result(timeout=5)

    def test_simultaneous_readers_only_observe_complete_json(self):
        done = threading.Event()

        def read():
            count = 0
            while not done.is_set():
                try:
                    json.loads(self.path.read_text())
                except PermissionError:
                    continue  # Sharing rejection isn't corrupt JSON.
                count += 1
            return count

        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(read)
            try:
                with reader_lock(self.path):
                    for n in range(25):
                        before = self.path.read_bytes()
                        try:
                            publish_atomic(self.path, {"seq": n, "points": [n] * 100})
                        except PublicationError:
                            # Tight non-delete-sharing readers can exhaust the
                            # bounded retry budget. Preserve, never truncate.
                            self.assertEqual(self.path.read_bytes(), before)
            finally:
                done.set()
            self.assertGreater(task.result(timeout=5), 0)
        publish_atomic(self.path, {"after_readers_close": True})
        self.assertEqual(
            json.loads(self.path.read_text()), {"after_readers_close": True}
        )

    def test_command_publication_failure_never_republishes_in_handlers(self):
        for failed_call in [1, 3, 4]:  # Initial, acquisition, final publication.
            reader = Mock(started=True)
            reader.latest.return_value = {}
            reader.read_once.return_value = {}
            command = Command(stderr=io.StringIO())

            def publish(*args):
                if publish_mock.call_count == failed_call:
                    raise PublicationError("fixture disk failure")

            with patch(
                "apps.agriculture.management.commands.lidar_usb.SerialLidarProvider",
                return_value=reader,
            ), patch(
                "apps.agriculture.management.commands.lidar_usb.publish_atomic",
                side_effect=publish,
            ) as publish_mock, patch(
                "apps.agriculture.management.commands.lidar_usb.time.sleep",
                side_effect=KeyboardInterrupt,
            ):
                with self.assertRaisesRegex(CommandError, "fixture disk failure"):
                    command.run_reader(
                        {"port": "FAKE", "revision": "fixture", "baud": 115200},
                        self.path,
                    )
                self.assertEqual(publish_mock.call_count, failed_call)
                reader.close.assert_called_once()

    def test_sensor_failure_not_masked_by_terminal_publication_failure(self):
        reader = Mock()
        reader.start.side_effect = ValueError("original sensor fixture failure")
        command = Command(stderr=io.StringIO())
        with patch(
            "apps.agriculture.management.commands.lidar_usb.SerialLidarProvider",
            return_value=reader,
        ), patch(
            "apps.agriculture.management.commands.lidar_usb.publish_atomic",
            side_effect=[None, PublicationError("terminal disk failure")],
        ) as publish:
            with self.assertRaisesRegex(
                CommandError, "original sensor fixture failure"
            ):
                command.run_reader(
                    {"port": "FAKE", "revision": "fixture", "baud": 115200}, self.path
                )
            self.assertEqual(publish.call_count, 2)
            self.assertIn("terminal disk failure", command.stderr._out.getvalue())
