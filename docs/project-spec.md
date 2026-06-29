# 项目文件规格说明

> 最后更新: 2026-06-27

## 项目概述

**工具中心 (Tool Hub)** — 集成多个业务工具的全栈 Web 应用。后端 FastAPI + Pydantic + httpx + SQLite，前端 Vue 3 + Vite + TypeScript + vue-router。Python >=3.13，包管理 uv。

## 数据存储

- `uploads/tool_state.db` — SQLite，三张表：
  - `tool_state`: 工具表单状态持久化（key-value）
  - `pdd_orders`: PDD 订单流程状态
  - `product_info`: 商品信息（含重量）

## 新增模块

### product_weight.py (pdd_order/)
- `product_info` 表: item_id, item_name, weight, category 等 14 个字段
- `random_pick_items(N)`: 随机选取 N 个商品
- `calculate_order_weight(items)`: sum(itemWeight × quantity)
- API: `GET/POST /api/pdd-order/product-weight`

## 项目概述

**工具中心 (Tool Hub)** — 集成多个业务工具的全栈 Web 应用。后端 FastAPI + Pydantic + httpx，前端 Vue 3 + Vite + TypeScript + vue-router。Python >=3.13，包管理 uv。

---

## 后端 (src/tool_hub/)

### 核心模块

#### `src/tool_hub/__init__.py`
包入口，创建全局单例。
- **registry**: `ToolRegistry` 实例 — 全局工具注册中心

#### `src/tool_hub/config.py`
- **类 `Settings`** (pydantic-settings): 目录/端口配置

#### `src/tool_hub/logging.py`
- **函数 `setup_logging()`**: structlog 配置
- **函数 `redact_sensitive_fields()`**: PII 脱敏

#### `src/tool_hub/main.py`
FastAPI 应用 + 路由。见 [完整规格](#router-pdd) 的 API 列表。

#### `src/tool_hub/models.py`
- **类 `ToolMeta`**: 工具元信息（id/name/description/input_schema/hidden）
- **类 `ExecuteRequest`**: 执行请求（tool_id/params/file_id）
- **类 `ToolResult`**: 执行结果（success/message/data/errors）
- **类 `FileUploadResult`**: 上传结果

#### `src/tool_hub/tool_registry.py`
- **类 `ToolRegistry`**: 单例注册中心，register/list/get 方法

#### `src/tool_hub/tool_state.py`
- **函数 `get_state(tool_id)`** / **`save_state(tool_id, data)`**: JSON 文件持久化

### 工具基类

#### `tools/base.py`
- **类 `BaseTool`** (ABC): 

## API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tools` | 工具列表 |
| GET | `/api/tools/{tool_id}` | 工具详情 |
| POST | `/api/files/upload` | 文件上传 |
| POST | `/api/tools/execute` | 执行工具 |
| GET | `/api/tool-state/{tool_id}` | 获取状态 |
| POST | `/api/tool-state/{tool_id}` | 保存状态 |
| GET | `/api/health` | 健康检查 |

### Temu 网关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/temu-gateway/login` | 登录 |
| POST | `/api/temu-gateway/order` | 下单 |
| POST | `/api/temu-gateway/express-sheet` | 面单 |
| GET | `/api/temu-gateway/download/{filename}` | 下载 PDF |

### PDD-MN 流程
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/pdd-order/create` | 创建订单 |
| POST | `/api/pdd-order/tms-login` | TMS 登录 |
| POST | `/api/pdd-order/inbound` | 入库 |
| POST | `/api/pdd-order/auto-weigh` | 自动称重 |
| POST | `/api/pdd-order/manual-weigh` | 手动称重 |
| POST | `/api/pdd-order/shelf` | 上架 |
| POST | `/api/pdd-order/unpack` | 拆包通知 |
| POST | `/api/pdd-order/outbound` | 出库通知 |
| POST | `/api/pdd-order/bag` | 集包 |
| POST | `/api/pdd-order/vehicle` | 装车 |
| POST | `/api/pdd-order/dispatch` | 发车 |
| GET | `/api/pdd-order/route-nodes` | 路由节点 |
| POST | `/api/pdd-order/route` | 推送轨迹 |
| POST | `/api/pdd-order/batch` | 批量（SSE） |

### MIP 海关清关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/mip-customs/clear-state` | 清状态 |
| GET | `/api/mip-customs/results` | 查询结果 |
| POST | `/api/mip-customs/retry` | 重试 |
| GET | `/api/mip-customs/template` | 下载模板 |

### 推送重量
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/push-weight/query` | 查询 |
| POST | `/api/push-weight/push` | 推送 |

### 财务系统
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/financial-system/login` | 登录 |
| POST | `/api/financial-system/call` | 调 API |
| GET | `/api/financial-system/saved-body` | 获取保存的请求体 |

## 数据模型

### 通用
`ToolMeta`, `ExecuteRequest`, `ToolResult`, `FileUploadResult`

### MIP 海关清关
- **CustomsItem**: 海关申报单（含 Order, GoodsItem[], Sender, Receiver）
- **ImportBatch**: 导入结果汇总（success_count, failure_count, errors[]）
- **ImportRecord**: 状态记录（SQLite 表行）
- **ImportDefaults**: 导入默认值（dataclass）

### Temu 网关
- **LoginRequest / LoginResponse**: 登录请求/响应（含 get_auth/post_auth 鉴权头）
- **OrderRequest**: 下单请求
- **ExpressSheetRequest**: 面单请求（含 sheet_type 类型切换）

## 类与函数索引

### BaseTool (ABC)
`tool_id`, `tool_name`, `tool_description`, `get_meta()`, `execute(params, file_path)`

### ToolRegistry
`register(tool)`, `list_tools()`, `get_tool(tool_id)`, `tool_count`

### MIPAsyncClient
`_get_auth_headers()`, `_make_request()`, `create_item()`, `update_item()`

### ExcelImporter
`import_file(file_path, tracking_filter=None)` — 主入口

### ImportState
`is_processed()`, `mark_processed()`, `clear()`, `get_failed()`, `list_all()`

### TemuGatewayClient
`login()`, `place_order()`, `get_express_sheet()`, `get_last_mile_sheet()`

### PDDOrderClient
`create_order(body)` — MD5 签名后 POST

### 加密工具
- `aes_encrypt()` / `generate_secret()` / `generate_sign()` — Temu
- `sign_pdd()` / `md5()` — PDD

### 动态字段生成 (pdd_order)
`gen_logistics_order_code()`, `gen_buyer_code()`, `gen_dere_recog_code()`, `gen_mail_no()`, `gen_trade_order_sn()`

## 前端 (frontend/src/)

### 路由
| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | MainPage | 工具卡片导航 |
| `/tool/mip_customs_clearance` | MIPCustomsPage | MIP海关清关 |
| `/tool/temu_gateway` | TemuGatewayPage | Temu网关 |
| `/tool/pdd_order` | PDDOrderPage | PDD-MN流程 |
| `/tool/encoding_converter` | EncodingConverterPage | 编码转换 |
| `/tool/push_weight` | PushWeightPage | 推送重量 |
| `/tool/financial_system` | FinancialSystemPage | 财务系统 |

### 组件
| 组件 | 说明 |
|------|------|
| `ToolPanel.vue` | 通用工具面板（文件上传+参数+执行+结果） |
| `MIPImportTab.vue` | MIP 导入 Tab（上传/Token/执行/重试） |

### 页面组件
- **MainPage**: 工具卡片列表 + 导航
- **MIPCustomsPage**: 创建/更新双 Tab
- **TemuGatewayPage**: 登录/下单/面单三 Tab
- **PDDOrderPage**: 10 Tab 全流程（含自动勾选链 + 批量 SSE）
- **PushWeightPage**: 查询→确认→推送
- **FinancialSystemPage**: 登录 + 可扩展 API Tab

### API 封装 (api/index.ts)
`fetchTools`, `fetchToolDetail`, `uploadFile`, `executeTool`, `fetchToolState`, `saveToolState`, `temuLogin`, `pddCreateOrder`, `pddBag`, `pushWeightQuery`, `financialLogin`, `mipClearState` 等约 30 个函数
