# -*- coding: utf-8 -*-
"""
异步任务管理系统
- 线程池任务执行
- 任务状态追踪
- 进度实时查询
"""

import uuid
import threading
import time
import traceback
from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future
import queue


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 执行失败
    CANCELLED = "cancelled"   # 已取消


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 0-100
    message: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update_progress(self, progress: int, message: str = ""):
        """更新任务进度（线程安全）"""
        with self._lock:
            self.progress = min(100, max(0, progress))
            if message:
                self.message = message
            self.updated_at = time.time()

    def set_status(self, status: TaskStatus, message: str = ""):
        """更新任务状态（线程安全）"""
        with self._lock:
            self.status = status
            if message:
                self.message = message
            self.updated_at = time.time()

    def set_result(self, result: Any):
        """设置任务结果（线程安全）"""
        with self._lock:
            self.result = result
            self.status = TaskStatus.COMPLETED
            self.progress = 100
            self.updated_at = time.time()

    def set_error(self, error: str):
        """设置任务错误（线程安全）"""
        with self._lock:
            self.error = error
            self.status = TaskStatus.FAILED
            self.updated_at = time.time()


class TaskManager:
    """
    异步任务管理器
    使用线程池执行长时间运行的任务，支持进度追踪和结果查询
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式确保全局唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._tasks: Dict[str, TaskInfo] = {}
        self._futures: Dict[str, Future] = {}
        self._task_lock = threading.Lock()

        # 配置线程池
        self._max_workers = 4
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="TaskWorker-"
        )

        # 清理配置
        self._task_ttl = 3600  # 任务结果保留时间（秒）
        self._cleanup_interval = 300  # 清理检查间隔（秒）
        self._last_cleanup = time.time()

        # 启动后台清理线程
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="TaskCleanup"
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """后台清理过期任务"""
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup_expired_tasks()

    def _cleanup_expired_tasks(self):
        """清理过期任务"""
        current_time = time.time()
        with self._task_lock:
            expired_ids = []
            for task_id, task_info in self._tasks.items():
                if current_time - task_info.updated_at > self._task_ttl:
                    expired_ids.append(task_id)

            for task_id in expired_ids:
                del self._tasks[task_id]
                if task_id in self._futures:
                    del self._futures[task_id]

    def create_task(self) -> str:
        """
        创建新任务

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())[:12]
        task_info = TaskInfo(task_id=task_id)

        with self._task_lock:
            self._tasks[task_id] = task_info

        return task_id

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> None:
        """
        提交任务到线程池执行

        Args:
            task_id: 任务ID
            func: 要执行的函数
            *args, **kwargs: 函数参数
        """
        def _execute_with_progress():
            """包装函数：添加进度追踪"""
            task_info = self.get_task(task_id)
            if task_info is None:
                return

            task_info.set_status(TaskStatus.RUNNING, "任务开始执行")
            task_info.update_progress(5, "正在初始化...")

            try:
                # 包装函数以追踪进度
                def progress_callback(progress: int, message: str = ""):
                    task_info.update_progress(progress, message)

                # 添加进度回调到参数
                kwargs['_progress_callback'] = progress_callback

                # 执行主函数
                result = func(*args, **kwargs)
                task_info.set_result(result)

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                task_info.set_error(error_msg)

        # 提交到线程池
        future = self._executor.submit(_execute_with_progress)

        with self._task_lock:
            self._futures[task_id] = future

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            TaskInfo对象，如果不存在返回None
        """
        with self._task_lock:
            return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态（API友好格式）

        Args:
            task_id: 任务ID

        Returns:
            包含任务状态的字典
        """
        task_info = self.get_task(task_id)
        if task_info is None:
            return None

        with task_info._lock:
            return {
                "task_id": task_id,
                "status": task_info.status.value,
                "progress": task_info.progress,
                "message": task_info.message,
                "result": task_info.result,
                "error": task_info.error,
                "created_at": task_info.created_at,
                "updated_at": task_info.updated_at,
            }

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task_info = self.get_task(task_id)
        if task_info is None:
            return False

        with self._task_lock:
            if task_id in self._futures:
                future = self._futures[task_id]
                cancelled = future.cancel()
                if cancelled:
                    task_info.set_status(TaskStatus.CANCELLED, "任务已被取消")
                return cancelled

        return False

    def get_pool_status(self) -> Dict:
        """
        获取线程池状态

        Returns:
            线程池状态信息
        """
        with self._task_lock:
            active_count = sum(
                1 for f in self._futures.values()
                if f.running()
            )
            total_tasks = len(self._tasks)
            pending_tasks = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            )
            running_tasks = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.RUNNING
            )

        return {
            "max_workers": self._max_workers,
            "active_workers": active_count,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
        }


# 全局任务管理器实例
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    return task_manager
