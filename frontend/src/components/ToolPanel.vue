<script setup lang="ts">
/**
 * ToolPanel - 工具执行面板组件。
 *
 * 功能：
 * 1. 展示工具信息
 * 2. 支持文件上传
 * 3. 配置执行参数
 * 4. 点击执行并显示结果
 */
import { ref } from 'vue'
import { uploadFile, executeTool } from '../api'

// Props: 工具元信息
const props = defineProps<{
  tool: {
    tool_id: string
    tool_name: string
    description: string
    requires_file: boolean
    accepted_file_types: string[]
    input_schema: any
  }
}>()

// ================================================================
// 响应式状态
// ================================================================

/** 选中的文件 */
const selectedFile = ref<File | null>(null)
/** 上传后的文件 ID */
const fileId = ref<string>('')
/** 上传状态 */
const uploading = ref(false)
/** 执行状态 */
const executing = ref(false)
/** 执行结果 */
const result = ref<any>(null)
/** 错误信息 */
const errorMsg = ref('')

// ================================================================
// 执行参数 - 从 input_schema 动态生成
// ================================================================

/** 构建默认参数对象 */
function buildDefaultParams(): Record<string, any> {
  const params: Record<string, any> = {}
  if (props.tool.input_schema?.properties) {
    for (const [key, prop] of Object.entries(props.tool.input_schema.properties)) {
      const p = prop as any
      params[key] = p.default ?? ''
    }
  }
  return params
}

const execParams = ref<Record<string, any>>(buildDefaultParams())

// ================================================================
// 方法
// ================================================================

/** 文件选择处理 */
function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
    errorMsg.value = ''
  }
}

/** 上传文件 */
async function onUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  errorMsg.value = ''
  try {
    const res = await uploadFile(selectedFile.value)
    fileId.value = res.file_id
    result.value = null
    errorMsg.value = ''
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

/** 执行工具 */
async function onExecute() {
  if (executing.value) return
  executing.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const res = await executeTool(props.tool.tool_id, execParams.value, fileId.value || undefined)
    result.value = res
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '执行失败'
  } finally {
    executing.value = false
  }
}
</script>

<template>
  <div class="tool-panel">
    <!-- 工具信息 -->
    <div class="tool-header">
      <h3>{{ tool.tool_name }}</h3>
      <p class="tool-desc">{{ tool.description }}</p>
    </div>

    <!-- 文件上传区域 -->
    <div v-if="tool.requires_file" class="upload-area">
      <label class="upload-label">
        <span>选择文件</span>
        <input
          type="file"
          :accept="tool.accepted_file_types.join(',')"
          @change="onFileChange"
          class="upload-input"
        />
      </label>
      <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
      <button
        v-if="selectedFile"
        @click="onUpload"
        :disabled="uploading"
        class="btn btn-upload"
      >
        {{ uploading ? '上传中...' : '上传文件' }}
      </button>
      <span v-if="fileId" class="upload-success">✓ 已上传 (ID: {{ fileId }})</span>
    </div>

    <!-- 执行参数配置 -->
    <div v-if="tool.input_schema?.properties" class="params-area">
      <h4>执行参数</h4>
      <div
        v-for="(prop, key) in tool.input_schema.properties"
        :key="key"
        class="param-row"
      >
        <label :for="'param-' + key">{{ key }}</label>
        <!-- 下拉选择（enum 类型） -->
        <select
          v-if="prop.enum"
          :id="'param-' + key"
          v-model="execParams[key]"
          class="param-input"
        >
          <option v-for="opt in prop.enum" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <!-- 布尔类型 -->
        <input
          v-else-if="prop.type === 'boolean'"
          :id="'param-' + key"
          type="checkbox"
          v-model="execParams[key]"
        />
        <!-- 默认文本输入 -->
        <input
          v-else
          :id="'param-' + key"
          type="text"
          v-model="execParams[key]"
          class="param-input"
        />
        <span v-if="prop.description" class="param-hint">{{ prop.description }}</span>
      </div>
    </div>

    <!-- 执行按钮 -->
    <div class="action-area">
      <button
        @click="onExecute"
        :disabled="executing || (tool.requires_file && !fileId)"
        class="btn btn-execute"
      >
        {{ executing ? '执行中...' : '执行' }}
      </button>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMsg" class="error-area">
      <p class="error-text">{{ errorMsg }}</p>
    </div>

    <!-- 执行结果 -->
    <div v-if="result" class="result-area">
      <h4>
        执行结果:
        <span :class="result.success ? 'success-badge' : 'fail-badge'">
          {{ result.success ? '成功' : '失败' }}
        </span>
      </h4>
      <p>{{ result.message }}</p>
      <!-- 下载链接 -->
      <div v-if="result.data?.download_url" class="download-area">
        <a :href="result.data.download_url" target="_blank" class="btn btn-download">📥 下载转换后的文件</a>
      </div>
      <!-- 通用 KV 展示 -->
      <div v-if="result.data" class="result-kv">
        <table v-if="result.data.success_count !== undefined" class="kv-table">
          <tr><td>总行数</td><td>{{ result.data.total_rows }}</td></tr>
          <tr><td>处理行数</td><td>{{ result.data.processed_rows }}</td></tr>
          <tr><td>成功</td><td class="count-success">{{ result.data.success_count }}</td></tr>
          <tr><td>失败</td><td class="count-fail">{{ result.data.failure_count }}</td></tr>
          <tr><td>模式</td><td>{{ result.data.mode }}</td></tr>
        </table>
        <table v-else class="kv-table">
          <tr v-for="(v, k) in result.data" :key="k">
            <td>{{ k }}</td><td>{{ v }}</td>
          </tr>
        </table>
      </div>
      <!-- 错误详情 -->
      <div v-if="result.errors && result.errors.length > 0" class="error-details">
        <h4>错误详情 ({{ result.errors.length }})</h4>
        <ul>
          <li v-for="(err, idx) in result.errors" :key="idx">
            [行{{ err.row_number }}] {{ err.tracking_number }}: {{ err.message }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-panel {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  background: #fff;
}

.tool-header h3 {
  margin: 0 0 8px 0;
  color: #333;
}

.tool-desc {
  color: #666;
  font-size: 14px;
  margin: 0 0 16px 0;
}

/* 上传区域 */
.upload-area {
  margin-bottom: 16px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
}

.upload-label {
  display: inline-block;
  padding: 6px 16px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.upload-label:hover {
  background: #bbdefb;
}

.upload-input {
  display: none;
}

.file-name {
  margin-left: 12px;
  font-size: 14px;
  color: #555;
}

.upload-success {
  margin-left: 12px;
  color: #4caf50;
  font-size: 14px;
}

/* 参数区域 */
.params-area {
  margin-bottom: 16px;
}

.params-area h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #555;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.param-row label {
  min-width: 140px;
  color: #333;
}

.param-input {
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
  flex: 1;
  max-width: 400px;
}

.param-hint {
  color: #999;
  font-size: 12px;
}

/* 按钮 */
.action-area {
  margin-bottom: 12px;
}

.btn {
  padding: 8px 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-right: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-upload {
  background: #2196f3;
  color: #fff;
}

.btn-upload:hover:not(:disabled) {
  background: #1976d2;
}

.btn-execute {
  background: #4caf50;
  color: #fff;
}

.btn-execute:hover:not(:disabled) {
  background: #388e3c;
}

/* 错误区域 */
.error-area {
  padding: 8px 12px;
  background: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 4px;
  margin-bottom: 12px;
}

.error-text {
  color: #c62828;
  margin: 0;
  font-size: 14px;
}

/* 结果区域 */
.result-area {
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.result-area h4 {
  margin: 0 0 8px 0;
  font-size: 15px;
}

.success-badge {
  color: #2e7d32;
  font-weight: bold;
}

.fail-badge {
  color: #c62828;
  font-weight: bold;
}

.result-data table {
  width: 100%;
  max-width: 400px;
  border-collapse: collapse;
  margin-bottom: 12px;
}

.result-data td {
  padding: 4px 8px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
}

.result-kv {
  margin-top: 8px;
}

.kv-table {
  width: 100%;
  max-width: 500px;
  border-collapse: collapse;
}

.kv-table td {
  padding: 4px 8px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
  word-break: break-all;
}

.kv-table td:first-child {
  color: #888;
  width: 140px;
}

.download-area {
  margin: 10px 0;
}

.btn-download {
  display: inline-block;
  background: #4caf50;
  color: #fff;
  text-decoration: none;
  padding: 8px 20px;
  border-radius: 4px;
  font-size: 14px;
}

.btn-download:hover {
  background: #388e3c;
}

.count-success {
  color: #2e7d32;
  font-weight: bold;
}

.count-fail {
  color: #c62828;
  font-weight: bold;
}

.error-details {
  margin-top: 8px;
}

.error-details h4 {
  font-size: 13px;
  color: #c62828;
  margin: 0 0 4px 0;
}

.error-details ul {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.error-details li {
  margin-bottom: 2px;
  color: #d32f2f;
}
</style>
