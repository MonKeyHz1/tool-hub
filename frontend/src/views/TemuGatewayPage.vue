<script setup lang="ts">
/**
 * TemuGatewayPage - Temu 网关工具页面。
 *
 * 三合一面板：
 * - 登录鉴权（输入 appId + appSecret 获取 password）
 * - 下单（编辑/使用 JSON，提交订单）
 * - 获取面单（根据订单号查询并下载 PDF）
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { temuLogin, temuPlaceOrder, temuGetExpressSheet, fetchToolState } from '../api'

const router = useRouter()

// ================================================================
// 状态
// ================================================================

const activeTab = ref<'login' | 'order' | 'express'>('login')

const gatewayUrl = ref('https://testwebhook.staritgp.com/gateway')
const gatewayOptions = [
  { label: '测试环境', value: 'https://testwebhook.staritgp.com/gateway' },
  { label: '开发环境', value: 'http://192.168.110.70:9080' },
]

// --- 登录 ---
const loginAppId = ref('')
const loginAppSecret = ref('')
const loginLoading = ref(false)
const loginResult = ref<any>(null)
const loginError = ref('')

// --- 下单 ---
const orderAppId = ref('')
const orderPassword = ref('')
const orderJson = ref('{}')
const orderLoading = ref(false)
const orderResult = ref<any>(null)
const orderError = ref('')

// --- 面单 ---
const expressAppId = ref('')
const expressPassword = ref('')
const expressReferenceNo = ref('')
const expressWaybillNo = ref('')
const expressSheetType = ref('express')
const expressLoading = ref(false)
const expressResult = ref<any>(null)
const expressError = ref('')
const pdfDownloadUrl = ref('')

// ================================================================
// 方法
// ================================================================

/** 从登录结果自动填入下单和面单的 appId + password */
function autoFillCredentials(result: any) {
  if (result.success && result.app_id && result.password) {
    orderAppId.value = result.app_id
    orderPassword.value = result.password
    expressAppId.value = result.app_id
    expressPassword.value = result.password
  }
}

// --- 登录 ---
async function onLogin() {
  loginLoading.value = true
  loginError.value = ''
  loginResult.value = null
  try {
    const res = await temuLogin(loginAppId.value, loginAppSecret.value, gatewayUrl.value)
    loginResult.value = res
    autoFillCredentials(res)
  } catch (e: any) {
    loginError.value = e.response?.data?.message || e.message || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

// --- 下单 ---
async function onPlaceOrder() {
  orderLoading.value = true
  orderError.value = ''
  orderResult.value = null
  try {
    let body: any
    try {
      body = JSON.parse(orderJson.value)
    } catch {
      orderError.value = 'JSON 格式不正确'
      orderLoading.value = false
      return
    }
    const res = await temuPlaceOrder(orderAppId.value, orderPassword.value, body, gatewayUrl.value)
    orderResult.value = res
    // 下单成功后自动填入面单订单号和运单号
    if (res.success) {
      if (res.sent_order_number) expressReferenceNo.value = res.sent_order_number
      if (res.sent_waybill_no) expressWaybillNo.value = res.sent_waybill_no
    }
  } catch (e: any) {
    orderError.value = e.response?.data?.message || e.message || '下单失败'
  } finally {
    orderLoading.value = false
  }
}

// --- 面单 ---
async function onGetExpressSheet() {
  expressLoading.value = true
  expressError.value = ''
  expressResult.value = null
  pdfDownloadUrl.value = ''
  try {
    const res = await temuGetExpressSheet(
      expressAppId.value,
      expressPassword.value,
      expressReferenceNo.value,
      expressWaybillNo.value,
      expressSheetType.value,
      gatewayUrl.value,
    )
    expressResult.value = res
    if (res.pdf_url) {
      pdfDownloadUrl.value = res.pdf_url
    }
  } catch (e: any) {
    expressError.value = e.response?.data?.message || e.message || '查询失败'
  } finally {
    expressLoading.value = false
  }
}

// --- 加载上次保存的状态 ---
onMounted(async () => {
  try {
    const res = await fetchToolState('temu_gateway')
    if (res?.data) {
      const s = res.data
      // 登录
      if (s.login_appId) loginAppId.value = s.login_appId
      if (s.login_appSecret) loginAppSecret.value = s.login_appSecret
      // 下单
      if (s.order_appId) orderAppId.value = s.order_appId
      if (s.order_password) orderPassword.value = s.order_password
      if (s.order_json) {
        try {
          // 美化显示
          const parsed = JSON.parse(s.order_json)
          orderJson.value = JSON.stringify(parsed, null, 2)
        } catch {
          orderJson.value = s.order_json
        }
      }
      // 面单
      if (s.express_appId) expressAppId.value = s.express_appId
      if (s.express_password) expressPassword.value = s.express_password
      if (s.express_referenceNo) expressReferenceNo.value = s.express_referenceNo
      if (s.express_waybillNo) expressWaybillNo.value = s.express_waybillNo
      if (s.express_sheetType) expressSheetType.value = s.express_sheetType
    }
  } catch {
    // 忽略加载失败
  }
})
</script>

<template>
  <div class="temu-page">
    <!-- 顶部导航 -->
    <div class="top-bar">
      <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
      <h1>Temu 网关</h1>
      <select v-model="gatewayUrl" class="gw-select">
        <option v-for="g in gatewayOptions" :key="g.value" :value="g.value">{{g.label}}</option>
      </select>
    </div>

    <!-- Tab 切换 -->
    <div class="tabs">
      <button
        :class="['tab', { active: activeTab === 'login' }]"
        @click="activeTab = 'login'"
      >
        登录鉴权
      </button>
      <button
        :class="['tab', { active: activeTab === 'order' }]"
        @click="activeTab = 'order'"
      >
        下单
      </button>
      <button
        :class="['tab', { active: activeTab === 'express' }]"
        @click="activeTab = 'express'"
      >
        获取面单
      </button>
    </div>

    <!-- ================================================================ -->
    <!-- 登录鉴权面板 -->
    <!-- ================================================================ -->
    <div v-show="activeTab === 'login'" class="panel">
      <h3>登录鉴权</h3>
      <p class="desc">输入 appId 和 appSecret，生成加密鉴权参数 password</p>

      <div class="form-row">
        <label>appId</label>
        <input v-model="loginAppId" type="text" placeholder="输入 appId" class="input" />
      </div>
      <div class="form-row">
        <label>appSecret</label>
        <input v-model="loginAppSecret" type="text" placeholder="输入 appSecret（Base64 AES 密钥）" class="input" />
      </div>

      <button class="btn btn-primary" :disabled="loginLoading" @click="onLogin">
        {{ loginLoading ? '登录中...' : '登录' }}
      </button>

      <!-- 登录结果 -->
      <div v-if="loginError" class="error-box">{{ loginError }}</div>
      <div v-if="loginResult" class="result-box">
        <h4>登录结果: <span :class="loginResult.success ? 'success-tag' : 'fail-tag'">{{ loginResult.success ? '成功' : '失败' }}</span></h4>
        <div v-if="loginResult.success">
          <div class="kv"><span>appId:</span> {{ loginResult.app_id }}</div>
          <div class="kv"><span>password:</span> <code>{{ loginResult.password }}</code></div>
          <div class="kv"><span>有效期:</span> {{ loginResult.expires_in }}秒</div>

          <!-- GET 鉴权 -->
          <div v-if="loginResult.get_auth" class="auth-section">
            <h5>GET 请求鉴权头 <span class="auth-hint">（body = ""，查面单等）</span></h5>
            <div class="kv" v-for="(v, k) in loginResult.get_auth" :key="k">
              <span>{{ k }}:</span> <code>{{ v }}</code>
            </div>
          </div>

          <!-- POST 鉴权 -->
          <div v-if="loginResult.post_auth" class="auth-section">
            <h5>POST 请求鉴权头 <span class="auth-hint">（body = JSON，下单等）</span></h5>
            <div class="kv" v-for="(v, k) in loginResult.post_auth" :key="k">
              <span>{{ k }}:</span> <code>{{ v }}</code>
            </div>
          </div>
        </div>
        <div v-else class="error-text">{{ loginResult.message }}</div>
      </div>
    </div>

    <!-- ================================================================ -->
    <!-- 下单面板 -->
    <!-- ================================================================ -->
    <div v-show="activeTab === 'order'" class="panel">
      <h3>下单</h3>
      <p class="desc">编辑订单 JSON，使用登录获取的 password 提交</p>

      <!-- 占位符提示 -->
      <div class="hint-box">
        <strong>占位符说明：</strong>
        <ul>
          <li><code>{date}</code> → 当天日期（20260618）</li>
          <li><code>{ts}</code> → 毫秒时间戳（每次请求自动替换，防止重复）</li>
        </ul>
        <p class="hint-example">
          示例：<code>"orderNumber": "BG-{date}-{ts}"</code> →
          <code>"orderNumber": "BG-20260618-1718700123456"</code>
        </p>
      </div>

      <div class="form-row">
        <label>appId</label>
        <input v-model="orderAppId" type="text" placeholder="从登录结果自动填入" class="input" />
      </div>
      <div class="form-row">
        <label>password</label>
        <input v-model="orderPassword" type="text" placeholder="从登录结果自动填入" class="input" />
      </div>
      <div class="form-row">
        <label>订单 JSON</label>
        <textarea
          v-model="orderJson"
          rows="16"
          class="input json-input"
          placeholder="输入订单 JSON"
        ></textarea>
      </div>

      <button class="btn btn-primary" :disabled="orderLoading" @click="onPlaceOrder">
        {{ orderLoading ? '提交中...' : '提交订单' }}
      </button>

      <div v-if="orderError" class="error-box">{{ orderError }}</div>
      <div v-if="orderResult" class="result-box">
        <h4>下单结果: <span :class="orderResult.success ? 'success-tag' : 'fail-tag'">{{ orderResult.success ? '成功' : '失败' }}</span></h4>
        <div v-if="orderResult.sent_order_number || orderResult.sent_recipient_mobile || orderResult.sent_waybill_no" class="sent-info">
          <div v-if="orderResult.sent_order_number" class="kv"><span>实际 orderNumber:</span> <code>{{ orderResult.sent_order_number }}</code></div>
          <div v-if="orderResult.sent_waybill_no" class="kv"><span>运单号 waybillNo:</span> <code>{{ orderResult.sent_waybill_no }}</code></div>
          <div v-if="orderResult.sent_recipient_mobile" class="kv"><span>实际 recipientMobile:</span> <code>{{ orderResult.sent_recipient_mobile }}</code></div>
        </div>
        <pre v-if="orderResult.data" class="json-display">{{ JSON.stringify(orderResult.data, null, 2) }}</pre>
        <div v-else class="error-text">{{ orderResult.message }}</div>
      </div>
    </div>

    <!-- ================================================================ -->
    <!-- 面单面板 -->
    <!-- ================================================================ -->
    <div v-show="activeTab === 'express'" class="panel">
      <h3>获取面单</h3>
      <p class="desc">根据订单号/运单号查询面单，返回的 PDF 可下载</p>

      <div class="form-row">
        <label>面单类型</label>
        <select v-model="expressSheetType" class="input">
          <option value="express">标准面单 (express-sheet)</option>
          <option value="last_mile">尾程面单 (last-mile-sheet)</option>
        </select>
      </div>
      <div class="form-row">
        <label>appId</label>
        <input v-model="expressAppId" type="text" placeholder="从登录结果自动填入" class="input" />
      </div>
      <div class="form-row">
        <label>password</label>
        <input v-model="expressPassword" type="text" placeholder="从登录结果自动填入" class="input" />
      </div>
      <div v-if="expressSheetType === 'last_mile'" class="form-row">
        <label>运单号 (waybillNo)</label>
        <input v-model="expressWaybillNo" type="text" placeholder="下单后返回的运单号" class="input" />
      </div>
      <div class="form-row">
        <label>订单号 (referenceNo)</label>
        <input v-model="expressReferenceNo" type="text" placeholder="下单成功后自动填入" class="input" />
      </div>

      <button class="btn btn-primary" :disabled="expressLoading" @click="onGetExpressSheet">
        {{ expressLoading ? '查询中...' : '查询面单' }}
      </button>

      <div v-if="expressError" class="error-box">{{ expressError }}</div>
      <div v-if="expressResult" class="result-box">
        <h4>查询结果: <span :class="expressResult.success ? 'success-tag' : 'fail-tag'">{{ expressResult.success ? '成功' : '失败' }}</span></h4>
        <div v-if="pdfDownloadUrl" class="pdf-download">
          <a :href="pdfDownloadUrl" target="_blank" class="btn btn-download">📄 下载面单 PDF</a>
        </div>
        <pre v-if="expressResult.data" class="json-display">{{ JSON.stringify(expressResult.data, null, 2) }}</pre>
        <div v-else class="error-text">{{ expressResult.message }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.temu-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.top-bar h1 {
  font-size: 24px;
  margin: 0;
  flex: 1;
}

.env-hint {
  font-size: 12px;
  color: #999;
}

.back-btn {
  padding: 6px 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  background: #f5f5f5;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  border-bottom: 2px solid #e0e0e0;
}

.tab {
  padding: 10px 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 15px;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.2s, border-color 0.2s;
}

.tab:hover {
  color: #1976d2;
}

.tab.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
  font-weight: 600;
}

/* Panel */
.panel {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
}

.panel h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
}

.desc {
  color: #888;
  font-size: 13px;
  margin: 0 0 20px 0;
}

/* Hint */
.hint-box {
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 4px;
  font-size: 12px;
  color: #6d4c00;
}

.hint-box ul {
  margin: 4px 0 0 16px;
  padding: 0;
}

.hint-box li {
  margin-bottom: 2px;
}

.hint-box code {
  background: #fff3cd;
  padding: 1px 4px;
  border-radius: 2px;
}

.hint-example {
  margin-top: 6px;
  color: #8d6e63;
}

/* Form */
.form-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.form-row label {
  min-width: 120px;
  font-size: 13px;
  color: #555;
  line-height: 32px;
  text-align: right;
}

.input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
}

.json-input {
  font-family: 'Consolas', 'Monaco', monospace;
  resize: vertical;
}

/* Buttons */
.btn {
  padding: 8px 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-top: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #1976d2;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-download {
  display: inline-block;
  background: #4caf50;
  color: #fff;
  text-decoration: none;
  padding: 8px 20px;
  border-radius: 4px;
}

.btn-download:hover {
  background: #388e3c;
}

/* Results */
.error-box {
  margin-top: 12px;
  padding: 10px 14px;
  background: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 4px;
  color: #c62828;
  font-size: 13px;
}

.result-box {
  margin-top: 12px;
  padding: 14px;
  background: #f5f5f5;
  border-radius: 6px;
}

.result-box h4 {
  margin: 0 0 8px 0;
  font-size: 15px;
}

.success-tag {
  color: #2e7d32;
}

.fail-tag {
  color: #c62828;
}

.error-text {
  color: #c62828;
  font-size: 13px;
}

.auth-section {
  margin-top: 12px;
  padding: 10px 12px;
  background: #e8eaf6;
  border-radius: 4px;
  border-left: 3px solid #5c6bc0;
}

.auth-section h5 {
  font-size: 13px;
  color: #283593;
  margin: 0 0 6px 0;
}

.auth-hint {
  font-weight: normal;
  font-size: 11px;
  color: #7986cb;
}

.kv {
  font-size: 13px;
  margin-bottom: 4px;
  word-break: break-all;
}

.kv span {
  color: #888;
  margin-right: 4px;
}

.kv code {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.json-display {
  background: #263238;
  color: #aed581;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
  margin: 8px 0 0 0;
}

.pdf-download {
  margin: 8px 0;
}

.sent-info {
  margin-bottom: 8px;
  padding: 8px 10px;
  background: #e8f5e9;
  border-radius: 4px;
}
</style>
