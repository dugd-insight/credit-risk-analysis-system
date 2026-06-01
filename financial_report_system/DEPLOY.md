# 信贷风险分析系统 v3.0 — 部署文档

## 一、系统概述

**信贷风险分析系统**（Credit Risk Analysis System）是基于 FastAPI 构建的企业信用风险评估平台。系统解析企业财务报表（资产负债表、利润表、现金流量表），通过六维度评分模型（偿债能力、盈利能力、现金流、营运能力、税务合规、造假预警）生成专业的信用风险评估报告。

### 核心能力

| 功能 | 说明 |
|------|------|
| 多格式解析 | 支持 `.xls`（xlrd）和 `.xlsx`（openpyxl）两种 Excel 格式 |
| 期间类型识别 | 自动识别年报、季报（Q1/Q2/Q3）、月报，智能应用年化因子 |
| 六维评分体系 | 偿债/盈利/现金流/营运/税务/造假六维度 + Sigmoid 平滑评分 |
| Beneish M-Score | 完整 8 因子财务造假预警模型，支持一票否决 |
| 行业差异化 | 内置 6 大行业差异化权重（制造业、零售、担保、建筑、农业、通用） |
| 知识库规则 | 16 条风控规则，含监管依据、行业基准、授信建议 |
| 跨期趋势分析 | 支持多期数据对比，自动计算趋势指标 |
| HTML 报告 | 专业风险评估报告，含雷达图、趋势图、行业基准对照 |
| API 服务 | RESTful API，支持同步/异步分析、批量分析 |

### 技术栈

- **后端**: Python 3.11+ / FastAPI / Uvicorn
- **数据处理**: Pandas / xlrd / openpyxl
- **报告生成**: Chart.js 4.x（前端渲染）/ xhtml2pdf（可选 PDF）
- **部署**: Docker / Docker Compose

---

## 二、环境要求

### 硬件要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 10 GB | 50 GB+（取决于报告存储量） |

### 软件要求

| 环境 | 版本要求 |
|------|---------|
| Python | 3.11+（推荐 3.11 或 3.12） |
| Docker（可选） | 20.10+ |
| Docker Compose（可选） | 2.0+ |

### 支持的操作系统

- Linux（推荐 Ubuntu 22.04+ / CentOS 8+）
- Windows 10/11 / Windows Server 2019+
- macOS 12+

---

## 三、部署方式

### 方式 A：Docker 部署（推荐）

#### 3.1 克隆项目

```bash
git clone https://github.com/dugd-insight/credit-risk-analysis-system.git
cd credit-risk-analysis-system
```

#### 3.2 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 按需编辑（默认值即可直接运行）
vim .env
```

可配置项说明：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_PORT` | 8000 | 服务端口 |
| `LOG_LEVEL` | info | 日志级别（debug/info/warning/error） |
| `TASK_TIMEOUT` | 300 | 分析任务超时（秒） |
| `MAX_FILE_SIZE` | 50 | 最大上传文件大小（MB） |
| `PDF_ENABLED` | true | 是否启用 PDF 报告生成 |
| `MSCORE_SAFE` | -2.22 | M-Score 安全阈值 |
| `MSCORE_WARN` | -1.78 | M-Score 警告阈值 |

#### 3.3 构建与启动

```bash
# 构建镜像（首次或代码更新后执行）
docker compose -f docker/docker-compose.yml build

# 启动服务
docker compose -f docker/docker-compose.yml up -d

# 查看日志
docker compose -f docker/docker-compose.yml logs -f
```

#### 3.4 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 预期返回
# {"status":"healthy","version":"3.0","pdf_ready":true}
```

#### 3.5 常用运维命令

```bash
# 停止服务
docker compose -f docker/docker-compose.yml down

# 重启服务
docker compose -f docker/docker-compose.yml restart

# 查看服务状态
docker compose -f docker/docker-compose.yml ps

# 进入容器（调试用）
docker exec -it financial_report_system bash

# 清理旧镜像
docker image prune -f
```

---

### 方式 B：手动部署（开发/测试环境）

#### 3.1 克隆项目并创建虚拟环境

```bash
git clone https://github.com/dugd-insight/credit-risk-analysis-system.git
cd credit-risk-analysis-system

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

#### 3.3 初始化目录

```bash
mkdir -p uploads reports data static
```

#### 3.4 配置环境变量（可选）

```bash
cp .env.example .env
# 按需修改 .env 中的配置
```

#### 3.5 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 3.6 一键启动（Windows）

```cmd
start.bat
```

#### 3.7 一键启动（Linux/Mac）

```bash
chmod +x start.sh
./start.sh
```

---

### 方式 C：Nginx 反向代理（生产环境推荐）

使用 Nginx 作为反向代理，提供 HTTPS、静态文件缓存和负载均衡。

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /static/ {
        alias /opt/credit-risk-analysis-system/static/;
        expires 7d;
    }
}
```

---

## 四、API 接口说明

### 基础 URL

```
http://<host>:<port>
```

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面（上传表单） |
| GET | `/health` | 健康检查 |
| POST | `/api/analyze` | 同步分析（上传文件） |
| POST | `/api/analyze-async` | 异步分析（返回 task_id） |
| GET | `/api/task/{task_id}` | 查询异步任务状态 |
| GET | `/api/report/{filename}` | 下载报告 |
| POST | `/api/batch-analyze` | 批量分析（指定目录） |
| GET | `/api/system/status` | 系统状态 |
| POST | `/api/cleanup` | 清理过期报告 |
| GET | `/docs` | Swagger API 文档 |

### 核心接口调用示例

#### 同步分析

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "files=@资产负债表.xlsx" \
  -F "files=@利润表.xlsx" \
  -F "company_name=某某公司" \
  -F "industry=制造业" \
  -F "mode=comprehensive"
```

#### Python 调用

```python
import requests

files = [
    ('files', ('报表.xlsx', open('path/to/报表.xlsx', 'rb'))),
]
data = {
    'company_name': '某某公司',
    'industry': '制造业',
    'mode': 'comprehensive'
}

resp = requests.post('http://localhost:8000/api/analyze', files=files, data=data)
result = resp.json()

if result['success']:
    print(f"评分: {result['score']}, 等级: {result['grade']}")
    print(f"报告: {result['report_url']}")
```

---

## 五、支持的行业

| 行业名称 | 说明 |
|---------|------|
| 制造业 | 传统制造业企业 |
| 零售/批发 | 零售批发企业 |
| 担保/金融服务 | 担保公司、金融服务机构（含担保专项指标） |
| 建筑/地产 | 建筑工程、房地产开发 |
| 农业/食品 | 农业生产、食品加工 |
| 通用 | 未匹配以上行业时使用通用权重 |

> **注意**: 行业名称需与上述名称完全匹配（含斜杠）。不在列表中的行业将自动使用"通用"权重。

---

## 六、支持的报表格式

### 文件格式

| 格式 | 扩展名 | 引擎 | 说明 |
|------|--------|------|------|
| Excel 97-2003 | `.xls` | xlrd | 旧格式，仅支持格式化值（不支持公式） |
| Excel 2007+ | `.xlsx` | openpyxl | 推荐格式，支持公式求值（需 `data_only=True`） |

### 报表类型自动识别

系统会根据文件内容和月份自动识别报表类型：

| 类型 | 识别规则 | 年化因子 |
|------|---------|---------|
| 年报 | 12月 + 本期/累计比 < 20% | 1.0（不年化） |
| Q1 季报 | 3月 + 本期/累计比 25%-70% | 4.0 |
| Q2 季报 | 6月 + 本期/累计比 35%-70% | 2.0 |
| Q3 季报 | 9月 + 本期/累计比 60%-95% | 1.333 |
| 月报 | 其他情况 | 12/月份 |

> 季报的流量指标（收入、利润等）会自动乘以年化因子折算为年度数据，确保跨期可比性。

### Sheet 命名要求

系统通过关键词匹配识别 Sheet 类型：

| Sheet 类型 | 匹配关键词 |
|-----------|-----------|
| 资产负债表 | 含"资产负债" |
| 利润表 | 含"利润" |
| 现金流量表 | 含"现金流量"或"现金流" |

---

## 七、项目目录结构

```
financial_report_system/
├── app/                          # FastAPI Web 层
│   ├── main.py                   # 主应用入口（路由、API）
│   ├── config.py                 # 统一配置中心
│   ├── tasks.py                  # 异步任务管理
│   ├── api/                      # API 子包
│   ├── core/                     # 核心业务适配层
│   │   ├── analyzer.py           # 分析引擎编排
│   │   └── report_generator.py   # 报告生成适配
│   ├── templates/                # Jinja2 模板
│   │   └── index.html            # Web 上传表单
│   └── static/                   # 静态资源
│
├── risk_engine/                  # 核心分析引擎
│   ├── __init__.py               # 包初始化
│   ├── file_parser.py            # Excel 文件解析（1009行）
│   ├── risk_analyzer.py          # 六维风险评分引擎（920行）
│   ├── knowledge_base.py         # 16条风控规则（370行）
│   └── report_generator.py       # HTML 报告渲染（1389行）
│
├── docker/                       # Docker 部署
│   ├── Dockerfile                # 多阶段构建
│   └── docker-compose.yml        # 服务编排
│
├── data/                         # 财务报表数据（上传/手动）
├── reports/                      # 生成的分析报告
├── uploads/                      # 上传临时文件
│
├── requirements.txt              # Python 依赖清单
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略规则
├── .dockerignore                 # Docker 忽略规则
├── start.bat                     # Windows 一键启动
├── start.sh                      # Linux/Mac 一键启动
├── Dockerfile                    # 顶层 Dockerfile（快捷方式）
└── docker-compose.yml            # 顶层 Compose（快捷方式）
```

---

## 八、常见问题

### Q1: 上传的 XLS 文件解析出来全是空值

**原因**: `.xls` 文件中有公式但 xlrd 不支持公式求值。
**解决**: 在 Excel 中将文件另存为 `.xlsx` 格式后再上传。

### Q2: 报告中现金流量表为空

**原因**: 上传的 Excel 文件中缺少现金流量表 Sheet，或 Sheet 名称不含"现金流量"关键词。
**解决**: 确保文件包含名为"现金流量表"或含"现金流"关键词的 Sheet。

### Q3: Docker 构建时安装依赖超时

**原因**: pip 默认源在国外网络可能较慢。
**解决**: 在 Dockerfile 中添加镜像源：
```dockerfile
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### Q4: PDF 报告中文乱码

**原因**: 系统缺少中文字体。
**解决**: Docker 镜像已内置 WenQuanYi 字体。手动部署时需安装中文字体：
```bash
# Ubuntu
sudo apt install fonts-wqy-microhei fonts-wqy-zenhei
# CentOS
sudo yum install wqy-microhei-fonts wqy-zenhei-fonts
```

### Q5: 信用等级为 CCC（一票否决）

**原因**: Beneish M-Score 超过 -1.78 阈值，触发了财务造假预警的一票否决机制。
**解决**:
1. 检查财务数据是否有误
2. 如果确认数据正确但 M-Score 偏高（单期 M-Score 精度有限），可调高 `MSCORE_WARN` 阈值

### Q6: 端口 8000 被占用

**解决**:
```bash
# 修改端口
export SERVER_PORT=8001
# 或修改 .env 文件
# 或直接指定
uvicorn app.main:app --port 8001
```

---

## 九、更新与维护

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# Docker 部署：重新构建
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d

# 手动部署：重启服务
# 开发模式下 uvicorn --reload 会自动重载
# 生产模式下需手动重启
```

### 数据备份

```bash
# 备份报告和数据
tar -czf backup_$(date +%Y%m%d).tar.gz data/ reports/
```

### 日志查看

```bash
# Docker 部署
docker compose -f docker/docker-compose.yml logs --tail=100 -f

# 手动部署（查看 uvicorn 日志）
# 日志输出到标准输出，可重定向到文件
uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee server.log
```

---

## 十、安全建议

1. **生产环境务必配置 HTTPS**，使用 Nginx 反向代理 + Let's Encrypt 证书
2. **限制上传文件大小**，通过 `MAX_FILE_SIZE` 环境变量控制
3. **定期清理过期报告**，通过 `/api/cleanup` 接口或 cron 定时清理
4. **不要将 `.env` 文件提交到版本控制**（已在 `.gitignore` 中排除）
5. **敏感数据目录**（`data/`、`reports/`）应在系统层设置适当的访问权限

---

## 附录：快速部署清单

- [ ] Python 3.11+ 已安装
- [ ] 项目已克隆到目标服务器
- [ ] 虚拟环境已创建并激活
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] 目录已初始化（`uploads/`、`reports/`、`data/`）
- [ ] `.env` 配置已检查
- [ ] 服务已启动并通过健康检查
- [ ] 浏览器可访问 `http://<host>:8000`
- [ ] API 文档可访问 `http://<host>:8000/docs`
- [ ] 测试文件上传和分析流程正常
