"""任务调度器模块"""
import schedule
import time
import threading
from typing import Callable, Dict, Optional
from datetime import datetime

from .config import config
from .utils.logger import logger


class JobScheduler:
    """任务调度器"""

    def __init__(self):
        self.jobs: Dict[str, schedule.Job] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_job(self, name: str, func: Callable, interval_minutes: int):
        """添加定时任务"""
        if name in self.jobs:
            logger.warning(f"Job {name} already exists, skipping")
            return

        job = schedule.every(interval_minutes).minutes.do(func)
        self.jobs[name] = job
        logger.info(f"Added job: {name} (interval: {interval_minutes} minutes)")

    def remove_job(self, name: str):
        """移除任务"""
        if name in self.jobs:
            schedule.cancel_job(self.jobs[name])
            del self.jobs[name]
            logger.info(f"Removed job: {name}")

    def run_pending(self):
        """运行待执行的任务"""
        schedule.run_pending()

    def run(self):
        """运行调度器（阻塞）"""
        self._running = True
        logger.info("Scheduler started")

        while self._running:
            self.run_pending()
            time.sleep(config.check_interval)

    def start_background(self):
        """后台运行调度器"""
        self._running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logger.info("Scheduler started in background")

    def stop(self):
        """停止调度器"""
        self._running = False
        schedule.clear()
        self.jobs.clear()
        logger.info("Scheduler stopped")

    def get_jobs(self) -> Dict[str, Dict]:
        """获取所有任务状态"""
        jobs_status = {}
        for name, job in self.jobs.items():
            jobs_status[name] = {
                'next_run': job.next_run,
                'interval': job.interval
            }
        return jobs_status

    def get_next_run_time(self, name: str) -> Optional[datetime]:
        """获取任务下次运行时间"""
        if name in self.jobs:
            return self.jobs[name].next_run
        return None


# 全局调度器实例
scheduler = JobScheduler()
