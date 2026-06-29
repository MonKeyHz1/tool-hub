# 工具中心 (Tool Hub) - 快速上手

> 详细文档见 `docs/` 目录。

## 技术栈

后端 FastAPI + Pydantic + httpx，前端 Vue 3 + Vite + TypeScript + vue-router。

## 启动

```powershell
# 后端
cd D:\work\AITest\tool-hub
uv run python main.py            # http://localhost:8000

# 前端
cd frontend
npm run dev                      # http://localhost:5173
```

## 项目结构

```
src/tool_hub/                    # 后端
├── main.py                      # FastAPI 应用 + 挂载路由
├── config.py / logging.py       # 全局配置 / 日志
├── models.py                    # ToolMeta / ToolResult / ExecuteRequest
├── tool_registry.py             # 工具注册中心（单例）
├── tool_state.py                # 状态持久化（JSON，公共）
└── tools/                       # 6 个工具包
    ├── base.py                  # BaseTool ABC
    ├── mip_customs/             # MIP海关清关
    ├── temu_gateway/            # Temu网关
    ├── pdd_order/               # PDD-MN流程
    ├── encoding_converter/      # 编码转换
    ├── push_weight/             # 推送重量
    └── financial_system/        # 财务系统

frontend/src/                    # 前端
├── views/                       # 7 个工具页面
├── components/                  # ToolPanel / MIPImportTab
├── api/index.ts                 # axios 封装
├── router/index.ts              # 路由
└── main.ts / App.vue            # 入口
```

## 工具一览

| 工具 | 状态 | 最近改动 |
|------|------|------|
| MIP海关清关 | ✅ | SQLite去重+重试+Token切换 |
| Temu网关 | ✅ | 新增URL切换器（测试/开发环境） |
| PDD-MN流程 | 🔧 | 上门自提分离、商品表随机选品、称重查表算重 |
| 编码转换 | ✅ | 稳定 |
| 推送重量 | ✅ | 稳定 |
| 财务系统 | ✅ | 可扩展API Tab |

## 关键数据

- SQLite: `uploads/tool_state.db`（tool_state + pdd_orders + product_info）
- PDD 批量: 10单稳定，大于10单待验证
- 商品表: 2个初始商品（手表0.3kg、连衣裙0.15kg），可通过API管理

## 文档索引

| 文件 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 架构设计 + 技术要点 |
| [docs/project-spec.md](docs/project-spec.md) | 文件/类/函数规格说明（每次记录进度时更新） |
| [docs/guide-new-tool.md](docs/guide-new-tool.md) | 新增工具步骤指南 |
| [docs/python-notes.md](docs/python-notes.md) | Python/库知识笔记 |
| [docs/pitfalls.md](docs/pitfalls.md) | 踩坑记录（写代码前必读） |
