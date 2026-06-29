# 新增工具步骤指南

## 文件上传型工具（如 MIP 海关清关）

适合：上传文件 → 配置参数 → 执行 → 下载结果

**步骤**:

1. 创建 `src/tool_hub/tools/new_tool/` 目录
2. 写 `tool.py`，继承 `BaseTool`，实现 `get_meta()` 和 `execute()`
3. 在 `tools/__init__.py` 中 `registry.register(NewTool())`
4. 前端创建 `views/NewToolPage.vue`，使用 `<ToolPanel :tool="tool" />`
5. 在 `router/index.ts` 添加路由

**关键**: `input_schema` 定义参数，前端自动渲染表单。

---

## 多操作型工具（如 Temu、PDD-MN）

适合：无文件上传，多步骤操作，每步调用不同 API

**步骤**:

1. 创建 `src/tool_hub/tools/new_tool/` 目录
2. 创建以下文件：
   - `config.py` — 工具配置（环境变量）
   - `client.py` — HTTP 客户端封装
   - `models.py` — Pydantic 请求/响应模型
   - `router.py` — FastAPI APIRouter（定义 API 端点）
   - `tool.py` — 继承 `BaseTool`（占位）

3. 在 `main.py` 中挂载路由：
```python
from .tools.new_tool.router import router as new_tool_router
app.include_router(new_tool_router)
```

4. 在 `tools/__init__.py` 中注册：
```python
from .new_tool import NewTool
registry.register(NewTool())
```

5. 前端创建独立页面 `views/NewToolPage.vue`
6. 在 `router/index.ts` 添加路由

**关键**: 
- 路由前缀用 `prefix="/api/new-tool"`，避免冲突
- 每次请求前调用 `save_state()` 保存输入状态
- 页面 `onMounted` 时 `fetchToolState()` 恢复上次的值
