# -*- coding: utf-8 -*-
"""
统一配置中心
- 集中管理所有配置项
- 支持环境变量覆盖
- 提供配置验证
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import json


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"


@dataclass
class PathConfig:
    """路径配置"""
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    upload_dir: Path = field(init=False)
    report_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    static_dir: Path = field(init=False)
    template_dir: Path = field(init=False)

    def __post_init__(self):
        self.upload_dir = self.base_dir / "uploads"
        self.report_dir = self.base_dir / "reports"
        self.data_dir = self.base_dir / "data"
        self.static_dir = self.base_dir / "static"
        self.template_dir = self.base_dir / "templates"


@dataclass
class AnalysisConfig:
    """分析引擎配置"""
    # 任务超时时间（秒）
    task_timeout: int = 300

    # M-Score阈值
    mscore_safe_threshold: float = -2.22
    mscore_warning_threshold: float = -1.78

    # 评分权重
    default_weights: Dict[str, float] = field(default_factory=lambda: {
        'solvency': 0.30,
        'profitability': 0.25,
        'cashflow': 0.20,
        'operations': 0.12,
        'tax_compliance': 0.08,
        'fraud_alert': 0.05,
    })

    # 行业权重配置
    industry_weights: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        '制造业': {
            'solvency': 0.30, 'profitability': 0.25, 'cashflow': 0.20,
            'operations': 0.15, 'tax_compliance': 0.05, 'fraud_alert': 0.05,
        },
        '零售/批发': {
            'solvency': 0.25, 'profitability': 0.30, 'cashflow': 0.25,
            'operations': 0.15, 'tax_compliance': 0.05, 'fraud_alert': 0.00,
        },
        '担保/金融服务': {
            'solvency': 0.35, 'profitability': 0.20, 'cashflow': 0.15,
            'operations': 0.10, 'tax_compliance': 0.15, 'fraud_alert': 0.05,
        },
        '建筑/地产': {
            'solvency': 0.30, 'profitability': 0.20, 'cashflow': 0.25,
            'operations': 0.10, 'tax_compliance': 0.10, 'fraud_alert': 0.05,
        },
        '农业/食品': {
            'solvency': 0.28, 'profitability': 0.22, 'cashflow': 0.22,
            'operations': 0.13, 'tax_compliance': 0.10, 'fraud_alert': 0.05,
        },
        '通用': {
            'solvency': 0.30, 'profitability': 0.25, 'cashflow': 0.20,
            'operations': 0.12, 'tax_compliance': 0.08, 'fraud_alert': 0.05,
        },
    })


@dataclass
class FileConfig:
    """文件处理配置"""
    # 允许的文件扩展名
    allowed_extensions: set = field(default_factory=lambda: {'.xls', '.xlsx'})
    # 最大文件大小（MB）
    max_file_size_mb: int = 50
    # 单次最大文件数
    max_files_per_request: int = 20
    # 临时文件保留时间（秒）
    temp_file_ttl: int = 3600


@dataclass
class ReportConfig:
    """报告生成配置"""
    # HTML报告模板目录
    template_subdir: str = "templates"
    # 报告文件名前缀
    report_prefix: str = "risk_report"
    # PDF生成启用
    pdf_enabled: bool = True
    # 报告保留时间（小时）
    report_ttl_hours: int = 24


@dataclass
class CacheConfig:
    """缓存配置"""
    # 是否启用缓存
    enabled: bool = True
    # 缓存策略
    cache_strategy: str = "no-cache"
    # 版本号（用于缓存破坏）
    version: str = "3.0"


class Config:
    """
    全局配置类
    单例模式，统一管理所有配置
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Config._initialized:
            return

        Config._initialized = True

        # 基础目录
        self.base_dir = Path(__file__).parent.parent

        # 加载环境变量配置
        self._load_env_config()

        # 创建各模块配置
        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            reload=os.getenv("SERVER_RELOAD", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "info"),
        )

        self.paths = PathConfig(base_dir=self.base_dir)

        self.analysis = AnalysisConfig(
            task_timeout=int(os.getenv("TASK_TIMEOUT", "300")),
            mscore_safe_threshold=float(os.getenv("MSCORE_SAFE", "-2.22")),
            mscore_warning_threshold=float(os.getenv("MSCORE_WARN", "-1.78")),
        )

        self.files = FileConfig(
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE", "50")),
            max_files_per_request=int(os.getenv("MAX_FILES", "20")),
        )

        self.report = ReportConfig(
            pdf_enabled=os.getenv("PDF_ENABLED", "true").lower() == "true",
            report_ttl_hours=int(os.getenv("REPORT_TTL", "24")),
        )

        self.cache = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            version=os.getenv("APP_VERSION", "3.0"),
        )

        # 确保必要目录存在
        self._ensure_directories()

    def _load_env_config(self):
        """加载环境变量配置"""
        pass  # 环境变量在创建各配置类时直接读取

    def _ensure_directories(self):
        """确保必要目录存在"""
        for dir_path in [
            self.paths.upload_dir,
            self.paths.report_dir,
            self.paths.data_dir,
            self.paths.static_dir,
            self.paths.template_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_upload_dir(self) -> Path:
        """获取上传目录"""
        return self.paths.upload_dir

    def get_report_dir(self) -> Path:
        """获取报告目录"""
        return self.paths.report_dir

    def get_cache_headers(self) -> Dict[str, str]:
        """获取缓存控制响应头"""
        if not self.cache.enabled:
            return {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        return {
            "Cache-Control": f"{self.cache.cache_strategy}, max-age=0",
            "X-App-Version": self.cache.version,
        }

    def get_industry_weights(self, industry: str) -> Dict[str, float]:
        """获取指定行业的评分权重"""
        return self.analysis.industry_weights.get(
            industry,
            self.analysis.default_weights
        )

    def validate_file(self, filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        验证上传文件

        Returns:
            (是否有效, 错误信息)
        """
        # 检查扩展名
        ext = Path(filename).suffix.lower()
        if ext not in self.files.allowed_extensions:
            return False, f"不支持的文件格式: {ext}，仅支持 {', '.join(self.files.allowed_extensions)}"

        # 检查文件大小
        max_bytes = self.files.max_file_size_mb * 1024 * 1024
        if file_size > max_bytes:
            return False, f"文件大小超过限制: {file_size / 1024 / 1024:.1f}MB > {self.files.max_file_size_mb}MB"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "log_level": self.server.log_level,
            },
            "paths": {
                "upload_dir": str(self.paths.upload_dir),
                "report_dir": str(self.paths.report_dir),
            },
            "cache": {
                "enabled": self.cache.enabled,
                "version": self.cache.version,
            },
        }


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
