"""Run an export command and write wall-time/process-tree memory reports."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

from common import REPORTS_DIR, ROOT, rel_path


ACTIVE_ENV = "ENDFIELD_EXPORT_BENCHMARK_ACTIVE"
DEFAULT_SAMPLE_INTERVAL_SECONDS = 1.0
DEFAULT_COMMAND = [str(ROOT / "export.bat"), "--export-from-game", "--with-assets"]
WINDOWS_BATCH_EXTENSIONS = {".bat", ".cmd"}


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return slug or "export"


def format_bytes(value: int | None) -> str:
    if value is None:
        return "n/a"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(amount) < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{amount:.2f} TiB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {sec:04.1f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes):02d}m {sec:04.1f}s"


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def command_for_display(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return " ".join(subprocess.list2cmdline([item]) for item in command)


class WindowsProcessSampler:
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    MAX_PATH = 260

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    def __init__(self) -> None:
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self.kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self.kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(self.PROCESSENTRY32W),
        ]
        self.kernel32.Process32FirstW.restype = wintypes.BOOL
        self.kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(self.PROCESSENTRY32W),
        ]
        self.kernel32.Process32NextW.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(self.PROCESS_MEMORY_COUNTERS_EX),
            wintypes.DWORD,
        ]
        self.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    def list_processes(self) -> dict[int, dict[str, Any]]:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        if snapshot == self.INVALID_HANDLE_VALUE:
            return {}
        try:
            entry = self.PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            processes: dict[int, dict[str, Any]] = {}
            if not self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                return processes
            while True:
                pid = int(entry.th32ProcessID)
                processes[pid] = {
                    "pid": pid,
                    "ppid": int(entry.th32ParentProcessID),
                    "name": entry.szExeFile,
                }
                if not self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
            return processes
        finally:
            self.kernel32.CloseHandle(snapshot)

    def query_memory(self, pid: int) -> dict[str, int] | None:
        access = self.PROCESS_QUERY_LIMITED_INFORMATION | self.PROCESS_VM_READ
        handle = self.kernel32.OpenProcess(access, False, pid)
        if not handle:
            return None
        try:
            counters = self.PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(counters)
            ok = self.psapi.GetProcessMemoryInfo(
                handle,
                ctypes.byref(counters),
                ctypes.sizeof(counters),
            )
            if not ok:
                return None
            return {
                "working_set_bytes": int(counters.WorkingSetSize),
                "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "private_bytes": int(counters.PrivateUsage),
                "pagefile_bytes": int(counters.PagefileUsage),
            }
        finally:
            self.kernel32.CloseHandle(handle)

    def sample(self, root_pid: int, elapsed_seconds: float) -> dict[str, Any]:
        processes = self.list_processes()
        tree_pids: set[int] = set()
        if root_pid in processes:
            tree_pids.add(root_pid)
        changed = True
        while changed:
            changed = False
            for pid, info in processes.items():
                if pid in tree_pids:
                    continue
                if int(info.get("ppid") or 0) in tree_pids:
                    tree_pids.add(pid)
                    changed = True

        entries: list[dict[str, Any]] = []
        inaccessible_pids: list[int] = []
        total_working_set = 0
        total_private = 0
        max_process_peak = 0
        for pid in sorted(tree_pids):
            info = processes.get(pid, {"pid": pid, "ppid": None, "name": ""})
            entry = {
                "pid": pid,
                "ppid": info.get("ppid"),
                "name": info.get("name") or "",
                "working_set_bytes": None,
                "peak_working_set_bytes": None,
                "private_bytes": None,
                "pagefile_bytes": None,
            }
            memory = self.query_memory(pid)
            if memory is None:
                inaccessible_pids.append(pid)
            else:
                entry.update(memory)
                total_working_set += memory["working_set_bytes"]
                total_private += memory["private_bytes"]
                max_process_peak = max(max_process_peak, memory["peak_working_set_bytes"])
            entries.append(entry)

        top_processes = sorted(
            entries,
            key=lambda item: int(item.get("working_set_bytes") or 0),
            reverse=True,
        )[:15]
        return {
            "elapsed_seconds": elapsed_seconds,
            "process_count": len(entries),
            "working_set_bytes": total_working_set,
            "private_bytes": total_private,
            "max_process_peak_working_set_bytes": max_process_peak,
            "inaccessible_pids": inaccessible_pids,
            "top_processes": top_processes,
        }


class NullProcessSampler:
    def sample(self, root_pid: int, elapsed_seconds: float) -> dict[str, Any]:
        return {
            "elapsed_seconds": elapsed_seconds,
            "process_count": None,
            "working_set_bytes": None,
            "private_bytes": None,
            "max_process_peak_working_set_bytes": None,
            "inaccessible_pids": [],
            "top_processes": [],
            "note": "process-tree memory sampling is only implemented on Windows",
        }


def make_sampler() -> WindowsProcessSampler | NullProcessSampler:
    if os.name != "nt":
        return NullProcessSampler()
    return WindowsProcessSampler()


def popen_command(command: list[str]) -> list[str]:
    if not command:
        raise ValueError("empty command")
    first = Path(command[0])
    if os.name == "nt" and first.suffix.lower() in WINDOWS_BATCH_EXTENSIONS:
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        return [comspec, "/d", "/c", *command]
    return command


def run_command(
    command: list[str],
    *,
    cwd: Path,
    sample_interval: float,
) -> dict[str, Any]:
    started = datetime.now().astimezone()
    start_perf = time.perf_counter()
    env = os.environ.copy()
    env[ACTIVE_ENV] = "1"
    sampler = make_sampler()
    peak_sample: dict[str, Any] | None = None
    samples = 0
    interrupted = False
    launch_error: str | None = None
    process: subprocess.Popen[Any] | None = None

    try:
        process = subprocess.Popen(popen_command(command), cwd=str(cwd), env=env)
    except OSError as exc:
        launch_error = f"{type(exc).__name__}: {exc}"

    returncode: int | None = None
    if process is not None:
        try:
            while True:
                elapsed = time.perf_counter() - start_perf
                sample = sampler.sample(process.pid, elapsed)
                samples += 1
                if (
                    peak_sample is None
                    or int(sample.get("working_set_bytes") or 0)
                    > int(peak_sample.get("working_set_bytes") or 0)
                ):
                    peak_sample = sample
                returncode = process.poll()
                if returncode is not None:
                    break
                time.sleep(sample_interval)
        except KeyboardInterrupt:
            interrupted = True
            process.terminate()
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                returncode = process.wait()
        else:
            returncode = process.returncode

    ended = datetime.now().astimezone()
    wall_seconds = time.perf_counter() - start_perf
    if peak_sample is None:
        peak_sample = {
            "elapsed_seconds": 0.0,
            "process_count": 0,
            "working_set_bytes": None,
            "private_bytes": None,
            "max_process_peak_working_set_bytes": None,
            "inaccessible_pids": [],
            "top_processes": [],
        }

    if launch_error:
        status = "launch_failed"
        returncode = 127
    elif interrupted:
        status = "interrupted"
    elif returncode == 0:
        status = "succeeded"
    else:
        status = "failed"

    return {
        "status": status,
        "returncode": returncode,
        "command": command,
        "command_display": command_for_display(command),
        "cwd": str(cwd.resolve()),
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": ended.isoformat(timespec="seconds"),
        "wall_seconds": wall_seconds,
        "sample_interval_seconds": sample_interval,
        "sample_count": samples,
        "peak_sample": peak_sample,
        "launch_error": launch_error,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    peak = payload.get("peak_sample") or {}
    reports = payload.get("reports") or {}
    lines = [
        "# Export Benchmark",
        "",
        f"- Command: `{payload.get('command_display')}`",
        f"- Working directory: `{payload.get('cwd')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Return code: `{payload.get('returncode')}`",
        f"- Started: `{payload.get('started_at')}`",
        f"- Ended: `{payload.get('ended_at')}`",
        (
            f"- Wall time: `{format_duration(float(payload.get('wall_seconds') or 0.0))}` "
            f"(`{float(payload.get('wall_seconds') or 0.0):.3f}` seconds)"
        ),
        (
            "- Peak sampled process-tree RAM: "
            f"`{format_bytes(peak.get('working_set_bytes'))}` working set"
        ),
        (
            "- Peak sampled process-tree private bytes: "
            f"`{format_bytes(peak.get('private_bytes'))}`"
        ),
        (
            "- Largest single-process peak working set seen at peak sample: "
            f"`{format_bytes(peak.get('max_process_peak_working_set_bytes'))}`"
        ),
        f"- Peak sample elapsed: `{format_duration(float(peak.get('elapsed_seconds') or 0.0))}`",
        f"- Peak sample process count: `{peak.get('process_count')}`",
        f"- Sample interval: `{payload.get('sample_interval_seconds')}` seconds",
        f"- Samples: `{payload.get('sample_count')}`",
    ]
    if payload.get("launch_error"):
        lines.append(f"- Launch error: `{payload.get('launch_error')}`")
    if peak.get("note"):
        lines.append(f"- Note: {peak.get('note')}")
    if peak.get("inaccessible_pids"):
        lines.append(
            "- Inaccessible PIDs at peak sample: "
            f"`{', '.join(str(pid) for pid in peak.get('inaccessible_pids') or [])}`"
        )
    if reports:
        lines.extend(
            [
                f"- JSON: `{reports.get('json')}`",
                f"- Markdown: `{reports.get('markdown')}`",
            ]
        )

    top_processes = peak.get("top_processes") or []
    if top_processes:
        lines.extend(
            [
                "",
                "## Top Processes At Peak Sample",
                "",
                "| pid | parent | name | working set | private bytes |",
                "| ---: | ---: | --- | ---: | ---: |",
            ]
        )
        for item in top_processes:
            lines.append(
                "| "
                f"{item.get('pid')} | "
                f"{item.get('ppid')} | "
                f"{md_escape(item.get('name') or '')} | "
                f"{format_bytes(item.get('working_set_bytes'))} | "
                f"{format_bytes(item.get('private_bytes'))} |"
            )

    return "\n".join(lines) + "\n"


def write_reports(payload: dict[str, Any], *, reports_dir: Path, label: str, update_latest: bool) -> tuple[Path, Path]:
    slug = safe_slug(label)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    out_dir = reports_dir / "export_benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{slug}_{run_id}.json"
    md_path = out_dir / f"{slug}_{run_id}.md"
    payload["reports"] = {
        "json": rel_path(json_path),
        "markdown": rel_path(md_path),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    if update_latest:
        latest_json = reports_dir / f"{slug}_benchmark_latest.json"
        latest_md = reports_dir / f"{slug}_benchmark_latest.md"
        payload["reports"]["latest_json"] = rel_path(latest_json)
        payload["reports"]["latest_markdown"] = rel_path(latest_md)
        latest_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        latest_md.write_text(build_markdown(payload), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an export command, sample process-tree memory, and write "
            "reports/export_benchmarks plus a latest benchmark report."
        )
    )
    parser.add_argument("--label", default="export", help="report filename label")
    parser.add_argument("--cwd", type=Path, default=ROOT, help="working directory for the command")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR, help="directory for benchmark reports")
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=DEFAULT_SAMPLE_INTERVAL_SECONDS,
        help="seconds between process-tree memory samples",
    )
    parser.add_argument("--no-latest", action="store_true", help="do not update the latest benchmark report")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command to run after --; defaults to export.bat --export-from-game --with-assets",
    )
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        args.command = list(DEFAULT_COMMAND)
    if args.sample_interval <= 0:
        parser.error("--sample-interval must be greater than 0")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload = run_command(
        list(args.command),
        cwd=args.cwd,
        sample_interval=float(args.sample_interval),
    )
    json_path, md_path = write_reports(
        payload,
        reports_dir=args.reports_dir,
        label=args.label,
        update_latest=not args.no_latest,
    )
    print(
        json.dumps(
            {
                "benchmark_json": rel_path(json_path),
                "benchmark_md": rel_path(md_path),
                "status": payload["status"],
                "returncode": payload["returncode"],
                "wall_seconds": round(float(payload["wall_seconds"]), 3),
                "peak_working_set_bytes": (payload.get("peak_sample") or {}).get("working_set_bytes"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return int(payload["returncode"] or 0)


if __name__ == "__main__":
    raise SystemExit(main())
