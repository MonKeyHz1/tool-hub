# Python 知识笔记

## 1. ABC 抽象基类

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    @abstractmethod
    def execute(self, params):
        ...  # 子类必须实现
```
`ABC` → 不能直接实例化。`@abstractmethod` → 子类不实现就报错。

## 2. 异步 async/await

```python
async def fetch_data():
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)   # 不阻塞，其他任务可继续
        return resp.json()
```
- `async def` → 异步函数，调用返回 coroutine
- `await` → 暂停当前函数直到异步操作完成，期间 CPU 可以切换其他任务
- FastAPI 原生支持 async，性能远高于同步

## 3. Pydantic 类型校验

```python
class LoginRequest(BaseModel):
    app_id: str = Field(..., description="应用 ID")
    app_secret: str = Field(..., description="密钥")
```
- 自动校验类型、自动生成 JSON Schema
- `...` 表示必填，也可以设默认值

## 4. pydantic-settings 环境变量

```python
class TemuGatewayConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TEMU_", env_file=".env")
    gateway_url: str = "https://default.com"
```
- 自动从 `.env` 读 `TEMU_GATEWAY_URL`
- 前缀隔离，每个 config 类互不干扰

## 5. 异步 Generator + SSE

```python
async def event_stream():
    yield f"data: {json.dumps({'msg':'hello'})}\n\n"  # 暂停，等前端消费

# 语法禁区
# ❌ 不能 return value
# ❌ 不能 yield int/bool（必须 str/bytes）
```

## 6. structlog 结构化日志

```python
logger = structlog.get_logger()
log = logger.bind(tool_id="xxx")
log.info("done", status="ok")
# 输出: [info] done  tool_id=xxx  status=ok
```

## 7. httpx 序列化陷阱

```python
# PDD 接口要求紧凑 JSON（无空格），签名和请求体格式必须一致
body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
rsp = await client.post(url, content=body_json.encode("utf-8"))

# ❌ 不要用 json=body（httpx 默认加空格，签名会错）
```

## 8. 数据库只读查询

```python
conn = pymysql.connect(...)
cur = conn.cursor()
cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
cur.execute("SELECT ...")
```
`READ UNCOMMITTED` 不锁表，适合只读查询。
