import argparse
import json
import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from platforms.batch_collector import run_daily_batch

load_dotenv()

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _incremental_batch_job():
    """4시간마다 호출하는 증분 배치 작업"""
    logger.info("=== 스케줄된 증분 배치 시작 ===")
    try:
        result = run_daily_batch(trigger_type="scheduled_incremental", mode="incremental")
        logger.info(
            f"증분 배치 완료: scraped={result.get('total_ads_scraped', 0)}, "
            f"new={result.get('total_ads_new', 0)}"
        )
    except Exception as e:
        logger.error(f"증분 배치 실패: {type(e).__name__}: {e}")


def _full_batch_job():
    """주 1회 전체 배치 작업"""
    logger.info("=== 스케줄된 전체 배치 시작 ===")
    try:
        result = run_daily_batch(trigger_type="scheduled_full", mode="full")
        logger.info(
            f"전체 배치 완료: scraped={result.get('total_ads_scraped', 0)}, "
            f"new={result.get('total_ads_new', 0)}"
        )
    except Exception as e:
        logger.error(f"전체 배치 실패: {type(e).__name__}: {e}")


def start_scheduler(
    incremental_hours: int = 4,
    full_day_of_week: str = "sun",
    full_hour: int = 3,
) -> BackgroundScheduler:
    global _scheduler

    incremental_hours = int(os.getenv("BATCH_INCREMENTAL_HOURS", str(incremental_hours)))
    full_day_of_week = os.getenv("BATCH_FULL_DAY", full_day_of_week)
    full_hour = int(os.getenv("BATCH_FULL_HOUR", str(full_hour)))

    _scheduler = BackgroundScheduler()

    # Job 1: 증분 수집 (N시간마다)
    _scheduler.add_job(
        _incremental_batch_job,
        trigger=CronTrigger(hour=f"*/{incremental_hours}"),
        id="incremental_batch_collection",
        name="Incremental Batch Ad Collection",
        replace_existing=True,
    )

    # Job 2: 전체 수집 (주 1회)
    _scheduler.add_job(
        _full_batch_job,
        trigger=CronTrigger(day_of_week=full_day_of_week, hour=full_hour, minute=0),
        id="full_batch_collection",
        name="Full Batch Ad Collection (weekly)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"스케줄러 시작: 증분 수집 매 {incremental_hours}시간, "
        f"전체 수집 매주 {full_day_of_week} {full_hour:02d}:00"
    )
    return _scheduler


def stop_scheduler() -> None:
    """스케줄러 중지"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 중지")
    _scheduler = None


def main(run_once: bool, daemon: bool, incremental_hours: int, full_day: str, full_hour: int, mode: str) -> dict:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if run_once:
        logger.info(f"=== 즉시 1회 실행 모드 (mode={mode}) ===")
        result = run_daily_batch(trigger_type="manual", mode=mode)
        logger.info(
            f"완료: scraped={result.get('total_ads_scraped', 0)}, "
            f"new={result.get('total_ads_new', 0)}"
        )
        return result

    if daemon:
        logger.info("=== 데몬 모드 시작 ===")
        scheduler = start_scheduler(
            incremental_hours=incremental_hours,
            full_day_of_week=full_day,
            full_hour=full_hour,
        )

        def _handle_signal(signum, frame):
            logger.info(f"시그널 {signum} 수신, 스케줄러 종료 중...")
            stop_scheduler()
            raise SystemExit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        while True:
            time.sleep(60)

    return {"error": "--run-once 또는 --daemon 중 하나를 지정하세요"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Scheduler - Incremental + Weekly Full")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-once", action="store_true", default=False, help="즉시 1회 실행 후 종료")
    group.add_argument("--daemon", action="store_true", default=False, help="스케줄러 데몬 모드")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full", help="1회 실행 시 모드")
    parser.add_argument("--incremental-hours", type=int, default=4, help="증분 수집 간격 (시간, 기본: 4)")
    parser.add_argument("--full-day", type=str, default="sun", help="전체 수집 요일 (기본: sun)")
    parser.add_argument("--full-hour", type=int, default=3, help="전체 수집 시각 (기본: 3)")
    args = parser.parse_args()

    result = main(
        run_once=args.run_once,
        daemon=args.daemon,
        incremental_hours=args.incremental_hours,
        full_day=args.full_day,
        full_hour=args.full_hour,
        mode=args.mode,
    )

    if args.run_once:
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"scheduler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"Saved: {output_file}")
