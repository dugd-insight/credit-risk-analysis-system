# -*- coding: utf-8 -*-
"""
信贷风险分析系统 - 应用初始化
"""

__version__ = "2.1.2"
__author__ = "Bank Credit Risk Team"

# 导出核心模块
from . import config
from . import tasks

__all__ = ["config", "tasks"]
