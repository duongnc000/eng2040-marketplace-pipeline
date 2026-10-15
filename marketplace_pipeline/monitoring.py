"""Scoped resource measurements, using only the Python standard library."""

import ctypes
import os
import sys
import tempfile
import threading
from pathlib import Path

from .config import DATABASE, ROOT


def python_size(value, seen: set[int] | None = None) -> int:
    """Size of reachable Python containers, counting shared references once.

    Native buffers and interpreter overhead outside these roots are excluded.
    """
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(python_size(k, seen) + python_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set, frozenset)):
        size += sum(python_size(item, seen) for item in value)
    return size


def rss_reader():
    """Return a current-process resident-memory reader, or None if unsupported."""
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
                    "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile",
                )
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        handle = kernel.GetCurrentProcess()
        api = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        api.restype = wintypes.BOOL

        def read():
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not api(handle, ctypes.byref(counters), counters.cb):
                raise ctypes.WinError(ctypes.get_last_error())
            return counters.working_set

        return read
    if Path("/proc/self/statm").exists():
        return lambda: int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    return None


class ResourceMonitor:
    """Sample RSS and scoped temporary file sizes about every 20 milliseconds.

    RSS includes retained objects and native allocations. Sampling can miss
    short peaks/files. Temporary scope: the redirected run directory and SQLite
    journal/WAL/SHM files beside DATABASE; not all OS or library caches.
    """

    def __enter__(self):
        base = ROOT / ".pipeline_tmp"
        base.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="step_", dir=base)
        self.path = Path(self.directory.name).resolve()
        if not self.path.is_relative_to(base.resolve()):
            raise ValueError("Temporary directory is outside the pipeline temporary root")
        self.old_environment = {key: os.environ.get(key) for key in ("TMP", "TEMP", "TMPDIR", "SQLITE_TMPDIR")}
        self.old_tempdir = tempfile.tempdir
        for key in self.old_environment:
            os.environ[key] = str(self.path)
        tempfile.tempdir = str(self.path)
        self.read_rss = rss_reader()
        self.peak_rss = None
        self.peak_temporary = 0
        self.error = None
        self.stop = threading.Event()
        self.sample()
        self.initial_rss = self.peak_rss
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()
        return self

    def sample(self):
        try:
            if self.read_rss is not None:
                self.peak_rss = max(self.peak_rss or 0, self.read_rss())
            paths = list(self.path.rglob("*")) + [
                Path(str(DATABASE) + suffix) for suffix in ("-journal", "-wal", "-shm")
            ]
            total = 0
            for path in paths:
                try:
                    if path.is_file():
                        total += path.stat().st_size
                except FileNotFoundError:
                    pass  # A temporary file can disappear between listing and stat.
            self.peak_temporary = max(self.peak_temporary, total)
        except OSError as error:
            self.error = str(error)

    def watch(self):
        while not self.stop.wait(.02):
            self.sample()

    def __exit__(self, *exception):
        self.stop.set()
        self.thread.join()
        self.sample()
        for key, value in self.old_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        tempfile.tempdir = self.old_tempdir
        self.directory.cleanup()
        if self.error and exception[0] is None:
            raise RuntimeError(f"Resource sampling failed: {self.error}")
