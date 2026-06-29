# 工具中心 (Tool Hub) - 架构设计

## 一、技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + Pydantic + httpx + structlog |
| 前端 | Vue 3 + Vite + TypeScript + vue-router |
| 包管理 | uv (pip 源使用清华镜像) |
| Python | >=3.13 |

## 二、核心概念

### 2.1 插件化工具架构

```
BaseTool (ABC 抽象基类)
  ├── 两个抽象方法：get_meta() 返回元信息，execute() 执行业务
  └── ToolRegistry 单例管理所有工具
```

新增工具只需继承 `BaseTool` → `registry.register()`，对现有代码零侵入。

### 2.2 两种路由模式

| 模式 | 适用场景 | 示例 |
|------|------|------|
| **通用 execute** | 文件上传类：上传→参数→执行 | MIP海关清关、编码转换 |
| **专属 router** | 多操作类：每个操作用独立 API 端点 | Temu网关、PDD-MN、财务系统 |

#### 通用 execute 流程
```
POST /api/files/upload  →  返回 file_id
POST /api/tools/execute →  传入 tool_id + params + file_id → BaseTool.execute()
```

#### 专属 router 流程
```
每个工具创建自己的 FastAPI APIRouter → 在 main.py 中 app.include_router(xxx_router)
```

### 2.3 状态持久化（公共能力）

`tool_state.py` — 所有工具共用：
- 每个工具在 `uploads/tool_state_{tool_id}.json` 中保存表单输入
- 后端每次请求前自动调用 `save_state()` 保存
- 前端 onMounted 时调用 `fetchToolState()` 恢复

### 2.4 配置分层

`pydantic-settings` — 每个工具独立 config 类：
```python
class MIPConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MIP_", env_file=".env")
    access_token: str = ""
```
从 `.env` 读同名环境变量，前缀隔离，不同工具不打架。

## 三、工具目录规范

```
src/tool_hub/tools/
├── base.py                  # BaseTool 基类 (ABC)
│
├── mip_customs/             # 文件上传型
│   ├── tool.py              #   继承 BaseTool
│   ├── client.py            #   异步 HTTP 客户端
│   ├── config.py            #   独立配置
│   ├── models.py            #   数据模型
│   └── ...
│
├── temu_gateway/            # 多操作型
│   ├── tool.py              #   继承 BaseTool
│   ├── router.py            #   专属 API 路由
│   ├── client.py            #   异步 HTTP 客户端
│   └── crypto_utils.py      #   AES + HMAC 工具
│
└── pdd_order/               # 多操作型 + DB
    ├── tool.py
    ├── router.py            #   下单/入库/称重/上架/拆包/出库/集包/装车/发车/轨迹
    ├── client.py            #   PDDOrderClient (MD5 签名)
    ├── sign_utils.py        #   MD5 签名工具
    ├── field_generator.py   #   动态字段生成
    └── config.py            #   含 DB、TMS 配置
```

## 四、关键技术点

### 4.1 异步 HTTP 客户端 (httpx)
```python
async with httpx.AsyncClient(timeout=30) as client:
    rsp = await client.post(url, json=body, headers=headers)
```
所有外部 API 调用全异步，不阻塞。

### 4.2 SSE 流式进度
```python
async def event_stream():
    yield f"event: step\ndata: {json.dumps({...})}\n\n"
return StreamingResponse(event_stream(), media_type="text/event-stream")
```
批量执行时实时推进度到前端。

### 4.3 加解密
- **AES-128-CBC**: `cryptography` 库，用于 Temu 登录加密
- **HMAC-SHA256**: 用于 Temu 请求签名
- **MD5**: 用于 PDD 请求签名

### 4.4 数据库
- **只读**: `READ UNCOMMITTED` 隔离级别，避免锁表
- **断点续传**: SQLite 记录处理状态
