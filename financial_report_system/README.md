# 🏦 信贷风险分析系统

> Bank Credit Risk Analysis System - 基于财务报表的企业信用风险评估平台

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

## 📋 项目简介

本系统是一款面向银行和金融机构的企业信贷风险分析工具，通过上传企业财务报表，自动进行多维度风险评估，生成专业的信用风险评估报告。

### 核心功能

- 📊 **多文件支持**：支持同时上传多期财务报表（.xls/.xlsx）
- 🔍 **智能识别**：自动识别报告期，支持跨期对比分析
- 🏦 **行业差异化**：支持6种行业分类，各维度权重可配置
- 📈 **六维评分体系**：偿债能力、盈利能力、现金流、营运能力、税务合规、造假预警
- 🎯 **Beneish M-Score**：财务造假预警模型（8因子完整计算）
- 📋 **知识库规则**：内置15条风控规则，自动触发预警
- 🌐 **异步任务处理**：支持长时间分析任务的进度轮询
- 📊 **实时进度显示**：前端展示分析进度，无需等待
- 🎨 **现代化界面**：渐变卡片设计，流畅动画体验
- 📥 **PDF导出**：生成完整PDF报告，可直接下载

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Web 前端 (HTML/CSS/JS)                   │
│                  http://localhost:8000                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API
┌─────────────────────────▼───────────────────────────────────┐
│                 FastAPI 后端服务 v2.1.2                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  同步分析API │  │ 异步任务API  │  │ 任务轮询API  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│               核心分析引擎 (risk_engine)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ file_parser  │  │risk_analyzer │  │report_gen    │      │
│  │  Excel解析   │  │  M-Score评分 │  │  HTML报告生成│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
cd docker
docker-compose up -d
# 访问 http://localhost:8000
```

### 方式二：本地运行

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```bash
start.bat
```

### 方式三：直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload
# 访问 http://localhost:8000
```

## 📁 项目结构

```
financial_report_system/
├── app/
│   ├── main.py              # FastAPI 主应用
│   ├── config.py            # 统一配置中心
│   ├── tasks.py             # 异步任务管理
│   ├── core/
│   │   ├── analyzer.py      # 分析引擎入口
│   │   └── report_generator.py
│   └── templates/
│       └── index.html       # 前端页面
├── risk_engine/
│   ├── file_parser.py       # Excel 文件解析
│   ├── risk_analyzer.py      # 六维分析+M-Score
│   ├── knowledge_base.py    # 风控规则知识库
│   └── report_generator.py  # HTML报告生成
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── start.sh
├── start.bat
└── README.md
```

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 |
| `/health` | GET | 健康检查 |
| `/api/analyze` | POST | 同步分析 |
| `/api/analyze-async` | POST | 异步分析（返回task_id） |
| `/api/task/{task_id}` | GET | 查询任务状态 |
| `/api/report/{filename}` | GET | 下载报告 |
| `/api/system/status` | GET | 系统状态 |
| `/api/cleanup` | POST | 清理过期报告 |

### API 使用示例

```bash
# 同步分析
curl -X POST http://localhost:8000/api/analyze \
  -F "company_name=测试公司" \
  -F "industry=担保/金融服务" \
  -F "files=@财务报表.xlsx"

# 异步分析
curl -X POST http://localhost:8000/api/analyze-async \
  -F "company_name=测试公司" \
  -F "industry=担保/金融服务" \
  -F "files=@财务报表.xlsx"

# 查询任务状态
curl http://localhost:8000/api/task/{task_id}
```

## 🏭 支持的行业

| 行业 | 偿债 | 盈利 | 现金流 | 营运 | 税务 | 造假 |
|------|------|------|--------|------|------|------|
| 担保/金融服务 | 35% | 20% | 15% | 10% | 15% | 5% |
| 制造业 | 30% | 25% | 20% | 15% | 5% | 5% |
| 零售/批发 | 25% | 30% | 25% | 15% | 5% | 0% |
| 建筑/地产 | 30% | 20% | 25% | 10% | 10% | 5% |
| 农业/食品 | 28% | 22% | 22% | 13% | 10% | 5% |
| 通用 | 30% | 25% | 20% | 12% | 8% | 5% |

## 🎯 信用评级

| 等级 | 分数 | 授信建议 |
|------|------|----------|
| AAA | 90-100 | 建议足额授信 |
| AA | 80-89 | 建议正常授信 |
| A | 70-79 | 审慎授信 |
| BBB | 60-69 | 附条件授信 |
| BB | 50-59 | 压缩授信额度 |
| B | 40-49 | 建议拒绝或强担保 |
| CCC | 0-39 | 建议拒绝授信 |

## 🔬 核心算法

### Beneish M-Score（8因子模型）

| 因子 | 含义 |
|------|------|
| DSRI | 应收账款指数 |
| GMI | 毛利率指数 |
| AQI | 资产质量指数 |
| SGI | 营收增长指数 |
| DEPI | 折旧指数 |
| SGAI | 销管费用指数 |
| TATA | 应计利润比率 |
| LVGI | 财务杠杆指数 |

**判别规则：**
- M-Score < -2.22 → 财务造假可能性低
- M-Score > -1.78 → 财务造假可能性高

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_HOST` | 0.0.0.0 | 服务地址 |
| `SERVER_PORT` | 8000 | 服务端口 |
| `LOG_LEVEL` | info | 日志级别 |
| `TASK_TIMEOUT` | 300 | 任务超时(秒) |
| `APP_VERSION` | 2.1.2 | 应用版本 |

## 📋 系统要求

- Python 3.11+
- Linux/macOS/Windows
- Docker (可选)

## 📄 许可证

本项目仅供内部使用，请遵守相关保密规定。

---

*© 2024 Bank Credit Risk Team*
