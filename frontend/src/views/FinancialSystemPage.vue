<script setup lang="ts">
/**
 * FinancialSystemPage - 财务系统工具页面。
 *
 * 支持扩展 API 列表：
 * - Tab 登录：TMS JWT 登录
 * - Tab 接口：每个 API 独立编辑 JSON、调用、查看结果
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { financialLogin, financialCallApi, financialGetSavedBody, fetchToolState } from '../api'

const router = useRouter()

// ================================================================
// API 列表定义（扩展新接口只需在此加一项）
// ================================================================
interface ApiDef {
  key: string
  label: string
  path: string
  defaultBody: Record<string, any>
}

const apiList: ApiDef[] = [
  {
    key: 'AddReceivableFinancialStatementDetail',
    label: '新增应收明细',
    path: '/FinancialStatement/AddReceivableFinancialStatementDetail',
    defaultBody: {
      financialStatementId: 0,
      goodType: 1,
      businessNumberList: [""],
      createUser: "",
      weight: 0,
      amount: 0,
    },
  },
  {
    key: 'AddPayFinancialStatementDetail',
    label: '新增应付明细',
    path: '/FinancialStatement/AddPayFinancialStatementDetail',
    defaultBody: {
      financialStatementId: 0,
      goodType: 1,
      businessNumberList: [""],
      createUser: "",
      weight: 0,
      amount: 0,
    },
  },
]

// ================================================================
// 状态
// ================================================================

// --- 登录 ---
const loginJobNumber = ref('')
const loginPassword = ref('')
const loginLoading = ref(false)
const loginToken = ref('')
const loginResult = ref<any>(null)
const loginError = ref('')

// --- API 调用 ---
const activeTab = ref('login')
const activeApi = ref<ApiDef>(apiList[0])

// 每个 API 的独立状态（响应式）
const apiBodyRefs = ref<Record<string, string>>({})
const apiLoadingRefs = ref<Record<string, boolean>>({})
const apiResultRefs = ref<Record<string, any>>({})
const apiErrorRefs = ref<Record<string, string>>({})

// 当前选中 API 的便捷 getter/setter
const currentBody = computed({
  get: () => apiBodyRefs.value[activeTab.value] || '{}',
  set: (v: string) => { apiBodyRefs.value[activeTab.value] = v },
})
const currentLoading = computed(() => apiLoadingRefs.value[activeTab.value] || false)
const currentResult = computed(() => apiResultRefs.value[activeTab.value] || null)
const currentError = computed(() => apiErrorRefs.value[activeTab.value] || '')

// ================================================================
// 方法
// ================================================================

onMounted(async () => {
  // 恢复登录状态
  try {
    const res = await fetchToolState('financial_system')
    if (res?.data) {
      if (res.data.login_job_number) loginJobNumber.value = res.data.login_job_number
      if (res.data.login_password) loginPassword.value = res.data.login_password
      if (res.data.login_token) loginToken.value = res.data.login_token
    }
  } catch { /* ignore */ }

  // 恢复各 API 的请求体
  for (const api of apiList) {
    apiBodyRefs.value[api.key] = JSON.stringify(api.defaultBody, null, 2)
    try {
      const r = await financialGetSavedBody(api.key)
      if (r?.data && Object.keys(r.data).length > 0) {
        apiBodyRefs.value[api.key] = JSON.stringify(r.data, null, 2)
      }
    } catch { /* ignore */ }
  }
})

// 登录
async function onLogin() {
  loginLoading.value = true
  loginError.value = ''
  loginResult.value = null
  try {
    const res = await financialLogin(loginJobNumber.value, loginPassword.value)
    loginResult.value = res
    if (res.success) {
      loginToken.value = res.token
    }
  } catch (e: any) {
    loginError.value = e.response?.data?.message || e.message || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

// 调用 API
async function onCallApi() {
  if (!loginToken.value) {
    apiErrorRefs.value[activeTab.value] = '请先登录'
    return
  }
  apiLoadingRefs.value[activeTab.value] = true
  apiErrorRefs.value[activeTab.value] = ''
  apiResultRefs.value[activeTab.value] = null
  try {
    let body: any
    try {
      body = JSON.parse(currentBody.value)
    } catch {
      apiErrorRefs.value[activeTab.value] = 'JSON 格式不正确'
      apiLoadingRefs.value[activeTab.value] = false
      return
    }
    const res = await financialCallApi(activeApi.value.key, activeApi.value.path, loginToken.value, body)
    apiResultRefs.value[activeTab.value] = res
  } catch (e: any) {
    apiErrorRefs.value[activeTab.value] = e.response?.data?.message || e.message || '调用失败'
  } finally {
    apiLoadingRefs.value[activeTab.value] = false
  }
}

const tabs = computed(() => [
  { key: 'login', label: '登录' },
  ...apiList.map(a => ({ key: a.key, label: a.label })),
])

// 切换 tab
function switchTab(key: string) {
  activeTab.value = key
  const api = apiList.find(a => a.key === key)
  if (api) activeApi.value = api
}
</script>

<template>
  <div class="fin-page">
    <div class="top-bar">
      <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
      <h1>财务系统</h1>
      <span class="env-tag">TMS 测试环境</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 登录 -->
    <div v-show="activeTab === 'login'" class="panel">
      <h3>TMS 登录</h3>
      <div class="form-row">
        <label>工号</label>
        <input v-model="loginJobNumber" type="text" class="input" />
      </div>
      <div class="form-row">
        <label>密码</label>
        <input v-model="loginPassword" type="password" class="input" />
      </div>
      <button class="btn btn-primary" :disabled="loginLoading" @click="onLogin">
        {{ loginLoading ? '登录中...' : '登录' }}
      </button>

      <div v-if="loginToken" class="token-box">
        <span>Token:</span> <code>{{ loginToken.substring(0, 60) }}...</code>
      </div>
      <div v-if="loginError" class="error-box">{{ loginError }}</div>
      <div v-if="loginResult && !loginResult.success" class="error-box">{{ loginResult.message }}</div>
    </div>

    <!-- API 面板（统一渲染当前选中，不用 v-for） -->
    <div v-if="activeTab !== 'login'" class="panel">
      <h3>{{ activeApi.label }}</h3>
      <p class="desc">POST {{ activeApi.path }}</p>

      <div class="form-row">
        <label>请求体</label>
        <textarea v-model="currentBody" rows="14" class="input json-input"></textarea>
      </div>

      <button
        class="btn btn-primary"
        :disabled="currentLoading || !loginToken"
        @click="onCallApi()"
      >
        {{ currentLoading ? '调用中...' : '调用' }}
      </button>

      <div v-if="currentError" class="error-box">{{ currentError }}</div>

      <div v-if="currentResult" class="result-box">
        <h4>
          响应:
          <span :class="currentResult.success ? 'success-tag' : 'fail-tag'">
            {{ currentResult.success ? '成功' : '失败' }}
          </span>
        </h4>
        <pre v-if="currentResult.data" class="json-display">{{ JSON.stringify(currentResult.data, null, 2) }}</pre>
        <div v-else class="error-text">{{ currentResult.message }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fin-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.top-bar h1 {
  font-size: 24px;
  margin: 0;
  flex: 1;
}

.env-tag {
  font-size: 12px;
  color: #1565c0;
  background: #e3f2fd;
  padding: 3px 8px;
  border-radius: 4px;
}

.back-btn {
  padding: 6px 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover { background: #f5f5f5; }

.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  border-bottom: 2px solid #e0e0e0;
}

.tab {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.tab:hover { color: #1976d2; }
.tab.active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 600; }

.panel {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
}

.panel h3 { margin: 0 0 4px 0; font-size: 18px; }
.desc { color: #888; font-size: 13px; margin: 0 0 20px 0; }

.form-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.form-row label {
  min-width: 80px;
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

.btn {
  padding: 8px 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-top: 8px;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #1976d2; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1565c0; }

.token-box {
  margin-top: 12px;
  padding: 8px 12px;
  background: #e8f5e9;
  border-radius: 4px;
  font-size: 12px;
}

.token-box code {
  background: #c8e6c9;
  padding: 2px 6px;
  border-radius: 3px;
}

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

.result-box h4 { margin: 0 0 8px 0; font-size: 15px; }
.success-tag { color: #2e7d32; }
.fail-tag { color: #c62828; }
.error-text { color: #c62828; font-size: 13px; }

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
</style>
