import logging
import subprocess
import sys
import uuid
from pathlib import Path

logger = logging.getLogger("batch_runner")

_batch_processes: dict[str, dict] = {}

_backend_dir = str(Path(__file__).resolve().parent.parent)


def start_batch_subprocess(mode: str, trigger_type: str, domain: str = "") -> str:
    job_id = uuid.uuid4().hex[:12]

    cmd = [
        sys.executable, "-m", "platforms.batch_collector",
        f"--mode={mode}",
        f"--trigger-type={trigger_type}",
    ]
    if domain:
        cmd.append(f"--domain={domain}")

    logger.info(f"Starting batch subprocess: job_id={job_id}, cmd={cmd}")

    proc = subprocess.Popen(
        cmd,
        cwd=_backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    _batch_processes[job_id] = {
        "job_id": job_id,
        "pid": proc.pid,
        "process": proc,
        "mode": mode,
        "trigger_type": trigger_type,
        "domain": domain,
    }

    logger.info(f"Batch subprocess started: job_id={job_id}, pid={proc.pid}")
    _cleanup_finished_processes()
    return job_id


def get_batch_process_status(job_id: str) -> dict:
    entry = _batch_processes.get(job_id)
    if not entry:
        return {"job_id": job_id, "status": "unknown"}

    proc = entry["process"]
    returncode = proc.poll()

    if returncode is None:
        return {"job_id": job_id, "pid": proc.pid, "status": "running"}

    return {
        "job_id": job_id,
        "pid": proc.pid,
        "status": "completed" if returncode == 0 else "failed",
        "returncode": returncode,
    }


def _cleanup_finished_processes():
    finished = [
        jid for jid, entry in _batch_processes.items()
        if entry["process"].poll() is not None
    ]
    for jid in finished:
        del _batch_processes[jid]
    if finished:
        logger.debug(f"Cleaned up {len(finished)} finished batch processes")
