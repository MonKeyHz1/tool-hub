/**
 * API 请求封装 - 与后端 FastAPI 服务通信。
 */

import axios from 'axios'

// 后端 API 基础地址（开发模式通过 Vite 代理，生产环境需修改）
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 分钟超时（大批量导入可能很慢）
})

// ====================================================================
// 工具相关接口
// ====================================================================

/** 获取所有可用工具列表 */
export async function fetchTools() {
  const { data } = await api.get('/tools')
  return data
}

/** 获取单个工具详情 */
export async function fetchToolDetail(toolId: string) {
  const { data } = await api.get(`/tools/${toolId}`)
  return data
}

// ====================================================================
// 文件上传接口
// ====================================================================

/** 上传文件 */
export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ====================================================================
// 工具执行接口
// ====================================================================

/** 执行工具 */
export async function executeTool(toolId: string, params: Record<string, any>, fileId?: string) {
  const { data } = await api.post('/tools/execute', {
    tool_id: toolId,
    params,
    file_id: fileId || null,
  })
  return data
}

// ====================================================================
// 健康检查
// ====================================================================

/** 健康检查 */
export async function healthCheck() {
  const { data } = await api.get('/health')
  return data
}

// ====================================================================
// Temu 网关专属接口
// ====================================================================

/** Temu 登录鉴权 */
export async function temuLogin(appId: string, appSecret: string, gatewayUrl: string = '') {
  const { data } = await api.post('/temu-gateway/login', {
    app_id: appId,
    app_secret: appSecret,
    gateway_url: gatewayUrl,
  })
  return data
}

/** Temu 下单 */
export async function temuPlaceOrder(appId: string, password: string, orderBody: Record<string, any>, gatewayUrl: string = '') {
  const { data } = await api.post('/temu-gateway/order', {
    app_id: appId,
    password,
    order_body: orderBody,
    gateway_url: gatewayUrl,
  })
  return data
}

/** Temu 获取上次保存的订单 JSON */
export async function temuGetLastOrder() {
  const { data } = await api.get('/temu-gateway/last-order')
  return data
}

/** Temu 查询面单 */
export async function temuGetExpressSheet(
  appId: string,
  password: string,
  referenceNo: string,
  waybillNo: string = '',
  sheetType: string = 'express',
  gatewayUrl: string = '',
) {
  const { data } = await api.post('/temu-gateway/express-sheet', {
    app_id: appId,
    password,
    reference_no: referenceNo,
    waybill_no: waybillNo,
    sheet_type: sheetType,
    gateway_url: gatewayUrl,
  })
  return data
}

/** Base64 转 PDF */
export async function base64ToPdf(base64: string) {
  const { data } = await api.post('/encoding-converter/base64-to-pdf', { base64 })
  return data
}

/** 清理上传目录文件 */
export async function cleanupUploadFiles() {
  const { data } = await api.post('/files/cleanup')
  return data
}

// ====================================================================
// 工具状态持久化接口（公共基础功能）
// ====================================================================

/** 获取工具上次保存的表单状态 */
export async function fetchToolState(toolId: string) {
  const { data } = await api.get(`/tool-state/${toolId}`)
  return data
}

/** 保存工具表单状态 */
export async function saveToolState(toolId: string, state: Record<string, any>) {
  const { data } = await api.post(`/tool-state/${toolId}`, state)
  return data
}

// ====================================================================
// PDD 集运下单专属接口
// ====================================================================

/** 获取 PDD 配置信息 */
export async function pddGetConfig() {
  const { data } = await api.get('/pdd-order/config')
  return data
}

/** PDD 创建订单 */
export async function pddCreateOrder(deliveryType: string, orderBody: Record<string, any>) {
  const { data } = await api.post('/pdd-order/create', {
    delivery_type: deliveryType,
    order_body: orderBody,
  })
  return data
}

/** PDD TMS 登录 */
export async function pddTmsLogin(jobNumber: string, password: string) {
  const { data } = await api.post('/pdd-order/tms-login', {
    job_number: jobNumber,
    password,
  })
  return data
}

/** PDD 揽收入库 */
export async function pddInbound(token: string, trackingNumber: string) {
  const { data } = await api.post('/pdd-order/inbound', {
    token,
    tracking_number: trackingNumber,
  })
  return data
}

/** PDD 自动称重 */
export async function pddAutoWeigh(trackcode: string, length: number, width: number, height: number, weight: number) {
  const { data } = await api.post('/pdd-order/auto-weigh', {
    trackcode, length, width, height, weight,
  })
  return data
}

/** PDD 手动称重 */
export async function pddManualWeigh(token: string, orderNumber: string, trackingNumber: string, length: number, width: number, height: number, weight: number) {
  const { data } = await api.post('/pdd-order/manual-weigh', {
    token, order_number: orderNumber, tracking_number: trackingNumber, length, width, height, weight,
  })
  return data
}

/** PDD 上架 */
export async function pddShelf(token: string, trackingNumber: string, warehouseCode: string, binCode: string) {
  const { data } = await api.post('/pdd-order/shelf', {
    token, tracking_number: trackingNumber, warehouse_code: warehouseCode, bin_code: binCode,
  })
  return data
}

/** PDD 拆包通知 */
export async function pddUnpack(logisticsOrderCode: string, buyerCode: string, mailNo: string, deliveryType: string, receiverDetail: Record<string, string>) {
  const { data } = await api.post('/pdd-order/unpack', {
    logistics_order_code: logisticsOrderCode,
    buyer_code: buyerCode,
    mail_no: mailNo,
    delivery_type: deliveryType,
    receiver_detail: receiverDetail,
  })
  return data
}

/** PDD 出库通知 */
export async function pddOutbound(logisticsOrderCode: string, buyerCode: string, mailNo: string, tradeOrderSn: string, deliveryType: string, orderItems: any[], receiverDetail: Record<string, string>, weight: number) {
  const { data } = await api.post('/pdd-order/outbound', {
    logistics_order_code: logisticsOrderCode,
    buyer_code: buyerCode,
    mail_no: mailNo,
    trade_order_sn: tradeOrderSn,
    delivery_type: deliveryType,
    order_items: orderItems,
    receiver_detail: receiverDetail,
    weight,
  })
  return data
}

/** PDD 集包 */
export async function pddBag(token: string, ppCode: string, mailNos: string, outboundType: number) {
  const { data } = await api.post('/pdd-order/bag', { token, pp_code: ppCode, mail_nos: mailNos, outbound_type: outboundType })
  return data
}

/** PDD 装车 */
export async function pddVehicle(token: string, bagNos: string) {
  const { data } = await api.post('/pdd-order/vehicle', { token, bag_nos: bagNos })
  return data
}

/** PDD 发车 */
export async function pddDispatch(token: string, vehicleId: number) {
  const { data } = await api.post('/pdd-order/dispatch', { token, vehicle_id: vehicleId })
  return data
}

/** PDD 路由节点列表 */
export async function pddRouteNodes() {
  const { data } = await api.get('/pdd-order/route-nodes')
  return data
}

/** PDD 推送轨迹 */
export async function pddRoute(token: string, vehicleId: number, nodeId: number, billNo: string) {
  const { data } = await api.post('/pdd-order/route', { token, vehicle_id: vehicleId, customer_route_node_id: nodeId, bill_lading_no: billNo })
  return data
}

/** PDD 批量（SSE） */
export function pddBatch(orderCount: number, bagSize: number, steps: string[], deliveryType: string, orderBody: Record<string, any>, token: string): EventSource {
  const params = new URLSearchParams()
  const url = `/api/pdd-order/batch`
  // SSE 通过 POST 不支持 EventSource natively, 用 fetch + ReadableStream
  return { url, body: { order_count: orderCount, bag_group_size: bagSize, steps, delivery_type: deliveryType, order_body: orderBody, token } } as any
}

// ====================================================================
// 推送重量专属接口
// ====================================================================

/** 查询快递单号对应的尾程单号 */
export async function pushWeightQuery(numbers: string[]) {
  const { data } = await api.post('/push-weight/query', { numbers })
  return data
}

/** 推送重量到 TMS 生产 */
export async function pushWeightPush(numbers: string[]) {
  const { data } = await api.post('/push-weight/push', { numbers })
  return data
}

// ====================================================================
// 财务系统专属接口
// ====================================================================

/** 财务系统 TMS 登录 */
export async function financialLogin(jobNumber: string, password: string) {
  const { data } = await api.post('/financial-system/login', {
    job_number: jobNumber,
    password,
  })
  return data
}

/** 财务系统调用 API */
export async function financialCallApi(apiKey: string, apiPath: string, token: string, body: Record<string, any>) {
  const { data } = await api.post('/financial-system/call', {
    api_key: apiKey,
    api_path: apiPath,
    token,
    body,
  })
  return data
}

/** 财务系统获取保存的请求体 */
export async function financialGetSavedBody(apiKey: string) {
  const { data } = await api.get('/financial-system/saved-body', {
    params: { api_key: apiKey },
  })
  return data
}

// ====================================================================
// MIP 海关清关专属接口
// ====================================================================

/** 清除 MIP 导入状态（去重记录） */
export async function mipClearState() {
  const { data } = await api.post('/mip-customs/clear-state')
  return data
}

/** 获取 MIP 导入每行结果 */
export async function mipFetchResults() {
  const { data } = await api.get('/mip-customs/results')
  return data
}

/** 获取 MIP 异步导入任务状态 */
export async function mipGetTaskStatus(taskId: string) {
  const { data } = await api.get(`/mip-customs/status/${taskId}`)
  return data
}

/** 重试 MIP 导入失败行 */
export async function mipRetryFailed(fileId: string, tokenEnv: string, useCreate: boolean) {
  const { data } = await api.post('/mip-customs/retry', {
    file_id: fileId,
    token_env: tokenEnv,
    use_create: useCreate,
  })
  return data
}
