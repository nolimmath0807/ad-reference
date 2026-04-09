import fcntl
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("batch_runner")

_batch_processes: dict[str, dict] = {}

_backend_dir = str(Path(__file__).resolve().parent.parent)
_logs_dir = Path(_backend_dir) / "logs"
_lock_path = "/tmp/ad-reference-batch.lock"


def start_batch_subprocess(mode: str, trigger_type: str, domain: str = "") -> str | None:
    # File-based lock to prevent TOCTOU race between has_running_batch() and actual start
    lock_fd = open(_lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fd.close()
        logger.warning("Another batch is starting (lock held), skipping")
        return None

    try:
        # Double-check inside lock
        if has_running_batch():
            logger.warning("Running batch detected inside lock, skipping")
            return None

        job_id = uuid.uuid4().hex[:12]

        cmd = [
            sys.executable, "-m", "platforms.batch_collector",
            f"--mode={mode}",
            f"--trigger-type={trigger_type}",
        ]
        if domain:
            cmd.append(f"--domain={domain}")

        logger.info(f"Starting batch subprocess: job_id={job_id}, cmd={cmd}")

        _logs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = _logs_dir / f"batch_{job_id}_{timestamp}.log"
        log_fh = open(log_file_path, "w")

        env = {**os.environ, "DB_POOL_MAX": "10", "DB_POOL_MIN": "1", "DB_CLOSE_ON_RETURN": "1"}

        proc = subprocess.Popen(
            cmd,
            cwd=_backend_dir,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env=env,
        )

        _batch_processes[job_id] = {
            "job_id": job_id,
            "pid": proc.pid,
            "process": proc,
            "mode": mode,
            "trigger_type": trigger_type,
            "domain": domain,
            "log_file": str(log_file_path),
            "_log_fh": log_fh,
        }

        logger.info(f"Batch subprocess started: job_id={job_id}, pid={proc.pid}")
        _cleanup_finished_processes()
        return job_id
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def get_batch_process_status(job_id: str) -> dict:
    entry = _batch_processes.get(job_id)
    if not entry:
        return {"job_id": job_id, "status": "unknown"}

    proc = entry["process"]
    returncode = proc.poll()

    if returncode is None:
        return {"job_id": job_id, "pid": proc.pid, "status": "running"}

    result = {
        "job_id": job_id,
        "pid": proc.pid,
        "status": "completed" if returncode == 0 else "failed",
        "returncode": returncode,
    }

    if returncode != 0 and entry.get("log_file"):
        log_path = Path(entry["log_file"])
        if log_path.exists():
            lines = log_path.read_text().splitlines()
            result["stderr_tail"] = "\n".join(lines[-50:])

    return result


def has_running_batch() -> bool:
    """실행 중인 배치 subprocess가 있는지 확인"""
    _cleanup_finished_processes()
    return any(
        entry["process"].poll() is None
        for entry in _batch_processes.values()
    )


def _cleanup_finished_processes():
    finished = [
        jid for jid, entry in _batch_processes.items()
        if entry["process"].poll() is not None
    ]
    for jid in finished:
        fh = _batch_processes[jid].get("_log_fh")
        if fh:
            fh.close()
        del _batch_processes[jid]
    if finished:
        logger.debug(f"Cleaned up {len(finished)} finished batch processes")
