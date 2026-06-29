# 工具中心 (Tool Hub)

集成多个业务工具的 Web 服务平台。支持通过前端页面上传文件、配置参数并执行工具。

## 架构

```
tool-hub/
├── main.py                      # 服务启动入口
├── pyproject.toml               # 项目配置
├── .env.example                 # 环境变量模板
├── src/tool_hub/                # 后端源码
│   ├── __init__.py              # 导出 registry
│   ├── main.py                  # FastAPI 应用
│   ├── config.py                # 全局配置
│   ├── logging.py               # 结构化日志
│   ├── models.py                # 通用数据模型
│   ├── tool_registry.py         # 工具注册中心
│   └── tools/                   # 工具目录
│       ├── base.py              # 工具基类
│       ├── mip_customs/         # MIP 海关清关工具
│       │   ├── tool.py          # 工具包装器
│       │   ├── client.py        # MIP API 客户端
│       │   ├── config.py        # 工具配置
│       │   ├── models.py        # 数据模型
│       │   ├── excel_import.py  # Excel 导入引擎
│       │   ├── import_config.py # 导入默认值
│       │   ├── import_state.py  # 导入状态
│       │   ├── exceptions.py    # 自定义异常
│       │   └── README.md        # 工具文档
│       └── ...                  # 未来新增的工具
├── frontend/                    # 前端源码
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── api/
│       └── components/
└── uploads/                     # 上传文件存储
```

## 快速开始

### 1. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入 MIP API 配置
# MIP_BASE_URL=https://mypost.mn
# MIP_ACCESS_TOKEN=your-token-here
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 启动后端

```bash
uv run python main.py
# 后端运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tools` | 获取工具列表 |
| GET | `/api/tools/{tool_id}` | 获取工具详情 |
| POST | `/api/files/upload` | 上传文件 |
| POST | `/api/tools/execute` | 执行工具 |
| GET | `/api/health` | 健康检查 |

## 新增工具

在 `tools/` 目录下创建新包，实现 `BaseTool` 接口，然后在 `tools/__init__.py` 中注册：

```python
# tools/my_tool/__init__.py
from .tool import MyTool
__all__ = ["MyTool"]

# tools/__init__.py 中添加
from .my_tool import MyTool
registry.register(MyTool())
```
