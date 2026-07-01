<script setup lang="ts">
/**
 * EncodingConverterPage - 编码转换工具页面。
 *
 * Tab 切换：编码转换 / Base64 转 PDF。
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchToolDetail, base64ToPdf } from '../api'
import ToolPanel from '../components/ToolPanel.vue'

const router = useRouter()
const toolId = 'encoding_converter'
const tool = ref<any>(null)
const loading = ref(true)
const activeTab = ref<'convert' | 'base64pdf'>('convert')

const base64Input = ref('')
const base64Loading = ref(false)
const base64Result = ref<any>(null)
const base64Error = ref('')

onMounted(async () => {
  try {
    tool.value = await fetchToolDetail(toolId)
  } catch (e) {
    console.error('加载工具详情失败', e)
  } finally {
    loading.value = false
  }
})

async function onBase64ToPdf() {
  if (!base64Input.value.trim()) return
  base64Loading.value = true
  base64Error.value = ''
  base64Result.value = null
  try {
    const r = await base64ToPdf(base64Input.value.trim())
    if (r.success) {
      base64Result.value = r.data
    } else {
      base64Error.value = r.message || '生成失败'
    }
  } catch (e: any) {
    base64Error.value = e.response?.data?.message || e.message || '请求失败'
  } finally {
    base64Loading.value = false
  }
}

function onDownload(url: string) {
  window.open(url, '_blank')
}
</script>

<template>
  <div class="tool-page">
    <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
    <div v-if="loading" class="status-msg">加载工具中...</div>
    <template v-else-if="tool">
      <h1>{{ tool.tool_name }}</h1>
      <div class="tabs">
        <button :class="['tab', { active: activeTab === 'convert' }]" @click="activeTab = 'convert'">编码转换</button>
        <button :class="['tab', { active: activeTab === 'base64pdf' }]" @click="activeTab = 'base64pdf'">Base64 转 PDF</button>
      </div>

      <div v-show="activeTab === 'convert'">
        <ToolPanel :tool="tool" />
      </div>

      <div v-show="activeTab === 'base64pdf'" class="panel">
        <label class="label">粘贴 Base64 文本</label>
        <textarea v-model="base64Input" rows="12" class="base64-textarea" placeholder="将 Base64 编码的 PDF 内容粘贴到此处..."></textarea>
        <button class="btn btn-primary" :disabled="base64Loading" @click="onBase64ToPdf">
          {{ base64Loading ? '生成中...' : '生成 PDF' }}
        </button>
        <div v-if="base64Error" class="err">{{ base64Error }}</div>
        <div v-if="base64Result" class="result">
          <span class="ok">✓ 生成成功</span>
          <span class="meta">{{ base64Result.filename }} ({{ (base64Result.size / 1024).toFixed(1) }} KB)</span>
          <button class="btn btn-download" @click="onDownload(base64Result.download_url)">下载 PDF</button>
        </div>
      </div>
    </template>
    <div v-else class="status-msg error">工具加载失败</div>
  </div>
</template>

<style scoped>
.tool-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.back-btn {
  padding: 6px 16px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 16px;
}

.back-btn:hover {
  background: #f5f5f5;
}

h1 {
  font-size: 24px;
  margin: 0 0 16px 0;
}

.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
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
}

.tab:hover {
  color: #1976d2;
}

.tab.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
  font-weight: 600;
}

.panel {
  padding: 8px 0;
}

.label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
}

.base64-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  resize: vertical;
  margin-bottom: 12px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #2196f3;
  color: #fff;
}

.btn-download {
  background: #4caf50;
  color: #fff;
  margin-left: 12px;
}

.err {
  padding: 8px 12px;
  background: #ffebee;
  color: #c62828;
  border-radius: 4px;
  font-size: 13px;
  margin-top: 12px;
}

.result {
  margin-top: 16px;
  padding: 12px;
  background: #f1f8e9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.ok {
  color: #2e7d32;
  font-weight: bold;
}

.meta {
  color: #555;
  font-size: 13px;
}

.status-msg {
  text-align: center;
  padding: 40px;
  color: #666;
}

.status-msg.error {
  color: #c62828;
}
</style>
