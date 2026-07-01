<script setup lang="ts">
/**
 * MIPImportTab - MIP 导入 Tab（上传/执行/结果/重试）。
 */
import { computed, onUnmounted, ref } from 'vue'
import { uploadFile, executeTool, mipFetchResults, mipRetryFailed, mipGetTaskStatus } from '../api'

const props = defineProps<{
  toolId: string
  title: string
  useCreate: boolean
}>()

defineEmits(['clearState'])

// --- 文件上传 ---
const selectedFile = ref<File | null>(null)
const fileId = ref('')
const uploading = ref(false)

// --- 高级选项 ---
const advancedOpen = ref(false)
const concurrency = ref(3)
const requestTimeout = ref(30)
const maxRetryAttempts = ref(3)
const retryWaitMin = ref(1.0)
const retryWaitMax = ref(10.0)
// --- 执行 ---
const tokenEnv = ref('test')
const executing = ref(false)
const execResult = ref<any>(null)
const execError = ref('')

// --- 结果 & 重试 ---
const rowResults = ref<any[]>([])
const resultsLoading = ref(false)
const retrying = ref<Set<string>>(new Set())
const failedNumbersText = ref('')
const copied = ref(false)

const failedNumbers = computed(() => rowResults.value.filter(r => r.status !== 'success').map(r => r.tracking_number))

function onFileChange(e: Event) {
  const t = (e.target as HTMLInputElement)
  if (t.files?.[0]) selectedFile.value = t.files[0]
}

async function onUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const r = await uploadFile(selectedFile.value)
    fileId.value = r.file_id
  } catch (e: any) {
    execError.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

// --- 异步任务轮询 ---
const taskId = ref('')
const taskStatus = ref('')
const taskProgress = ref(0)
const taskTotal = ref(0)
const taskMessage = ref('')
let pollTimer: number | null = null

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

onUnmounted(stopPolling)

async function pollTaskStatus(currentTaskId: string) {
  try {
    const s = await mipGetTaskStatus(currentTaskId)
    taskStatus.value = s.status
    taskProgress.value = s.progress || 0
    taskTotal.value = s.total || 0
    taskMessage.value = s.message || ''

    if (s.status === 'completed' || s.status === 'failed' || s.status === 'cancelled') {
      stopPolling()
      executing.value = false
      execResult.value = {
        success: s.status === 'completed' && s.result?.success,
        message: s.message,
        data: s.result || {},
        errors: s.errors || [],
      }
      if (s.status === 'failed') {
        execError.value = s.message || '导入失败'
      }
      onFetchResults()
    }
  } catch (e: any) {
    execError.value = e.response?.data?.detail || e.message || '查询任务状态失败'
    stopPolling()
    executing.value = false
  }
}

async function onExecute() {
  if (!fileId.value) return
  executing.value = true
  execError.value = ''
  execResult.value = null
  stopPolling()
  taskStatus.value = ''
  taskProgress.value = 0
  taskTotal.value = 0
  taskMessage.value = ''

  try {
    const r = await executeTool(props.toolId, { 
      token_env: tokenEnv.value,
      concurrency: concurrency.value,
      request_timeout: requestTimeout.value,
      max_retry_attempts: maxRetryAttempts.value,
      retry_wait_min: retryWaitMin.value,
      retry_wait_max: retryWaitMax.value,
    }, fileId.value)
    if (r.success && r.data?.task_id) {
      taskId.value = r.data.task_id
      await pollTaskStatus(taskId.value)
      if (taskStatus.value !== 'completed' && taskStatus.value !== 'failed' && taskStatus.value !== 'cancelled') {
        pollTimer = window.setInterval(() => pollTaskStatus(taskId.value), 1500)
      }
    } else {
      execError.value = r.message || '启动任务失败'
      executing.value = false
    }
  } catch (e: any) {
    execError.value = e.response?.data?.detail || e.message || '执行失败'
    executing.value = false
  }
}

async function onFetchResults() {
  resultsLoading.value = true
  try {
    const r = await mipFetchResults()
    rowResults.value = r.data || []
    failedNumbersText.value = failedNumbers.value.join('\n')
  } catch (e: any) {
    execError.value = e.message || '获取结果失败'
  } finally {
    resultsLoading.value = false
  }
}

async function onCopyFailedNumbers() {
  if (!failedNumbers.value.length) return
  try {
    await navigator.clipboard.writeText(failedNumbersText.value)
    copied.value = true
    setTimeout(() => copied.value = false, 1500)
  } catch {
    // fallback: select textarea
    const el = document.getElementById(`failed-numbers-${props.toolId}`) as HTMLTextAreaElement | null
    if (el) {
      el.select()
    }
  }
}

async function onRetry(trackingNumber: string) {
  if (!fileId.value || retrying.value.has(trackingNumber)) return
  retrying.value.add(trackingNumber)
  try {
    await mipRetryFailed(fileId.value, tokenEnv.value, props.useCreate)
  } catch (e: any) {
    execError.value = e.response?.data?.message || e.message || '重试失败'
  } finally {
    retrying.value.delete(trackingNumber)
    onFetchResults()
  }
}

/** 重试所有失败行 */
async function onRetryAll() {
  if (!fileId.value || retrying.value.size > 0) return
  retrying.value.add('__all__')
  try {
    const r = await mipRetryFailed(fileId.value, tokenEnv.value, props.useCreate)
    execResult.value = r
  } catch (e: any) {
    execError.value = e.response?.data?.message || e.message || '重试失败'
  } finally {
    retrying.value.delete('__all__')
    onFetchResults()
  }
}
</script>

<template>
  <div class="tab-panel">
    <!-- 上传区 -->
    <div class="form-row">
      <label class="upload-label">
        选择 Excel
        <input type="file" accept=".xlsx,.xls" @change="onFileChange" />
      </label>
      <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
      <button v-if="selectedFile" class="btn btn-upload" :disabled="uploading" @click="onUpload">
        {{ uploading ? '上传中...' : '上传' }}
      </button>
      <span v-if="fileId" class="ok">✓ 已上传 ({{ fileId }})</span>
      <a href="/api/mip-customs/template" target="_blank" class="btn btn-tpl">下载模板</a>
    </div>

    <!-- 参数 & 执行 -->
    <div class="form-row">
      <label>Token</label>
      <select v-model="tokenEnv" class="select">
        <option value="test">测试环境</option>
        <option value="prod">生产环境</option>
      </select>
      <button class="btn btn-exec" :disabled="executing || !fileId" @click="onExecute">
        {{ executing ? '执行中...' : '执行' }}
      </button>
      <button class="btn btn-clear" @click="$emit('clearState')">清状态</button>
      <button class="btn btn-adv" @click="advancedOpen = !advancedOpen">
        {{ advancedOpen ? '隐藏高级' : '高级选项' }}
      </button>
    </div>

    <!-- 高级选项 -->
    <div v-if="advancedOpen" class="advanced-panel">
      <div class="adv-row">
        <label>并发数</label>
        <input v-model.number="concurrency" type="number" min="1" max="20" class="adv-input" />
        <span class="adv-hint">同时请求数，默认 3</span>
      </div>
      <div class="adv-row">
        <label>请求超时(秒)</label>
        <input v-model.number="requestTimeout" type="number" min="5" max="120" class="adv-input" />
        <span class="adv-hint">单个请求超时，默认 30</span>
      </div>
      <div class="adv-row">
        <label>重试次数</label>
        <input v-model.number="maxRetryAttempts" type="number" min="0" max="10" class="adv-input" />
        <span class="adv-hint">单条失败重试次数，默认 3</span>
      </div>
      <div class="adv-row">
        <label>重试最小等待(秒)</label>
        <input v-model.number="retryWaitMin" type="number" min="0.1" step="0.1" class="adv-input" />
        <span class="adv-hint">默认 1.0</span>
      </div>
      <div class="adv-row">
        <label>重试最大等待(秒)</label>
        <input v-model.number="retryWaitMax" type="number" min="0.1" step="0.1" class="adv-input" />
        <span class="adv-hint">默认 10.0</span>
      </div>
    </div>

    <div v-if="execError" class="err">{{ execError }}</div>

    <!-- 任务进度 -->
    <div v-if="executing || taskStatus" class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: taskTotal ? `${(taskProgress / taskTotal) * 100}%` : '0%' }"></div>
      </div>
      <div class="progress-text">
        <span v-if="taskStatus">{{ taskStatus }} — </span>
        <span>{{ taskMessage }}</span>
        <span v-if="taskTotal"> ({{ taskProgress }}/{{ taskTotal }})</span>
      </div>
    </div>

    <!-- 执行摘要 -->
    <div v-if="execResult" class="summary">
      <span :class="execResult.success ? 'ok' : 'fail'">
        {{ execResult.success ? '✓ 成功' : '✗ 失败' }}
      </span>
      <span>{{ execResult.message }}</span>
      <button v-if="execResult.data?.failure_count" class="btn btn-retry" @click="onRetryAll">
        重试全部失败
      </button>
      <button class="btn btn-results" @click="onFetchResults">查看详细结果</button>
    </div>

    <!-- 逐行结果 -->
    <div v-if="rowResults.length" class="table-wrap">
      <div class="failed-summary" v-if="failedNumbers.length">
        <div class="failed-title">
          失败/重复单号（共 {{ failedNumbers.length }} 个）
          <button class="btn btn-copy" @click="onCopyFailedNumbers" :disabled="copied">
            {{ copied ? '已复制' : '复制全部' }}
          </button>
        </div>
        <textarea
          :id="`failed-numbers-${toolId}`"
          class="failed-textarea"
          readonly
          rows="4"
          v-model="failedNumbersText"
          @click="($event.target as HTMLTextAreaElement).select()"
        ></textarea>
      </div>

      <table>
        <thead>
          <tr><th>运单号</th><th>状态</th><th>失败原因</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rowResults" :key="r.tracking_number" :class="r.status === 'success' ? 'row-ok' : 'row-fail'">
            <td><code>{{ r.tracking_number }}</code></td>
            <td>
              <span v-if="r.status === 'success'" class="tag-ok">成功</span>
              <span v-else-if="r.status === 'duplicate'" class="tag-dup">重复</span>
              <span v-else class="tag-fail">失败</span>
            </td>
            <td class="msg">{{ r.error_message || '—' }}</td>
            <td>
              <button v-if="r.status !== 'success'" class="btn btn-retry-sm"
                :disabled="retrying.has(r.tracking_number)"
                @click="onRetry(r.tracking_number)">
                {{ retrying.has(r.tracking_number) ? '重试中' : '重试' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-panel { padding: 8px 0; }
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.form-row label { font-size: 13px; color: #555; min-width: 60px; }
.upload-label { display: inline-block; padding: 6px 14px; background: #e3f2fd; color: #1976d2; border-radius: 4px; cursor: pointer; font-size: 13px; }
.upload-label input { display: none; }
.file-name { font-size: 13px; color: #555; }
.select { padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.btn { padding: 6px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-upload { background: #2196f3; color: #fff; }
.btn-tpl { background: #607d8b; color: #fff; text-decoration: none; padding: 6px 14px; font-size: 13px; }
.btn-exec { background: #4caf50; color: #fff; }
.btn-clear { background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
.btn-clear:hover { background: #ffcdd2; }
.btn-adv { background: #e3f2fd; color: #1976d2; border: 1px solid #bbdefb; }
.advanced-panel { padding: 12px; background: #f5f5f5; border-radius: 4px; margin-bottom: 10px; }
.adv-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.adv-row label { min-width: 110px; font-size: 12px; color: #555; }
.adv-input { width: 70px; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; }
.adv-hint { font-size: 11px; color: #888; }
.btn-retry, .btn-retry-sm { background: #ff9800; color: #fff; }
.btn-results { background: #9c27b0; color: #fff; }
.ok { color: #2e7d32; font-size: 13px; }
.fail { color: #c62828; font-size: 13px; }
.err { padding: 8px 12px; background: #ffebee; color: #c62828; border-radius: 4px; font-size: 13px; margin: 8px 0; }
.summary { padding: 10px 12px; background: #f5f5f5; border-radius: 4px; display: flex; align-items: center; gap: 12px; margin: 8px 0; }
.progress-wrap { margin: 10px 0; }
.progress-bar { width: 100%; height: 10px; background: #e0e0e0; border-radius: 5px; overflow: hidden; }
.progress-fill { height: 100%; background: #1976d2; transition: width 0.3s ease; }
.progress-text { font-size: 12px; color: #555; margin-top: 4px; }
.failed-summary { margin-bottom: 12px; padding: 10px 12px; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 4px; }
.failed-title { display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: #e65100; margin-bottom: 6px; }
.failed-textarea { width: 100%; box-sizing: border-box; font-family: monospace; font-size: 12px; resize: vertical; }
.btn-copy { background: #ff9800; color: #fff; }
.table-wrap { margin-top: 12px; max-height: 500px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 5px 8px; border-bottom: 1px solid #e0e0e0; text-align: left; }
th { background: #fafafa; color: #666; }
code { background: #e8e8e8; padding: 1px 4px; border-radius: 2px; }
.row-ok { background: #f1f8e9; }
.row-fail { background: #fff3e0; }
.tag-ok { color: #2e7d32; font-weight: bold; }
.tag-dup { color: #f57c00; }
.tag-fail { color: #c62828; font-weight: bold; }
.msg { color: #666; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
