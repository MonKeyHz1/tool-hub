# 踩坑记录

每次写代码前过一遍。

## Python 语法禁区

| # | 错误写法 | 正确写法 |
|---|------|------|
| 1 | `if x: async for m in gen(): yield m` | 换行 + 缩进 |
| 2 | `return True`（在含 yield 的函数里）| `return` 或 `yield True` |
| 3 | `x=1; if x: print(x)` | 换行，`if` 独占一行 |
| 4 | `async for m in gen(): yield m` （SSE 里 yield int/bool）| 必须是 str |

## Vue 陷阱

| # | 错误 | 正确 |
|---|------|------|
| 5 | `v-for` 里 `v-model="s.m"` 绑定 ref | 直接绑定原始 `ref`，不要通过数组项 |
| 6 | 用 `-replace` 管道改 Vue 文件 | 永远用 Edit 工具 |

## 文件操作

| # | 错误 | 结果 | 教训 |
|---|------|------|------|
| 7 | `Set-Content` 写 Vue 文件 | UTF-16LE 编码破坏中文 | 永远用 Edit 工具 |
| 8 | `-replace` 管道改源码 | 转义符破坏模板语法 | 永远用 Edit 工具 |

## 逻辑陷阱

| # | 错误 | 结果 |
|---|------|------|
| 9 | 中文步骤名 → 直接匹配英文 key (`"入库" in ["inbound"]`) | 找不到 |
| 10 | 字段名 `customerRouteNodeId` ↔ `customerRoutingNodeId` 来回改 | 两次都失败 |
| 11 | 不确定字段名就改代码 | 先用 Postman 验证 |
