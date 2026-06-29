# MIP 海关清关批量导入工具

## 功能说明

通过上传 Excel 文件，批量创建或更新 MIP 海关清关申报数据。

## Excel 模板要求

- 第 1 行：中文表头（标题行）
- 第 2 行：英文标识符（必须有）
- 第 3 行起：数据行

### 必需列

| 英文标识符 | 说明 |
|---|---|
| TRACKING_NUMBER/MAIL_ID | 运单号/邮件ID |
| GOODS_NM | 商品名称 |
| QTY | 商品数量 |
| CONSIGNEE_NM1 | 收货人姓名 |

### 可选列

| 英文标识符 | 说明 |
|---|---|
| MAIL_BAG_NUMBER | 邮袋号 |
| QTY_UNIT | 数量单位 |
| HSCODE | HS编码 |
| CONSIGNEE_CNTRY_CD | 收货人国家代码 |
| CONSIGNEE_CNTRY_NM | 收货人国家名称 |
| CONSIGNEE_ADDR | 收货人地址 |
| CONSIGNEE_TEL | 收货人电话 |
| WGT | 总重量 |
| NET_WGT | 净重 |
| SHIPPER_NM1 | 发货人姓名（可覆盖默认值） |
| SHIPPER_CNTRY_CD | 发货人国家代码（可覆盖默认值） |
| ... | 其他发货人/公司字段 |

## 执行参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| mode | string | update | create=创建, update=更新 |
| sender_country_code | string | CN | 发货人国家代码 |
| sender_country_name | string | CHINA | 发货人国家名称 |
| sender_nationality | string | CNN | 发货人国籍代码 |
| sender_name_1 | string | - | 发货人姓名 |
| sender_address | string | - | 发货人地址 |
| price | string | 0.00 | 商品默认单价 |
| price_currency | string | RMB | 价格货币代码 |
| clear_state | boolean | false | 是否清除去重记录 |

## 结果说明

- `success_count`: 成功提交的数量
- `failure_count`: 失败的数量
- `errors`: 失败详情（行号、运单号、错误类型和消息）

## 注意事项

- 一个运单号对应一个 API 请求
- 同一个运单号的多行商品会合并为一个请求
- 默认情况下会跳过已成功处理的运单号（由 SQLite 记录）
- 认证失败会立即中止所有后续处理
