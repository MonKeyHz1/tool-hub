<script setup lang="ts">
/**
 * MainPage - 工具中心主页面，展示所有可用工具的导航按钮。
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchTools, cleanupUploadFiles } from '../api'

const router = useRouter()

interface ToolInfo {
  tool_id: string
  tool_name: string
  description: string
}

const tools = ref<ToolInfo[]>([])
const loading = ref(true)
const error = ref('')
const cleanupLoading = ref(false)
const cleanupMsg = ref('')

onMounted(async () => {
  try {
    const data = await fetchTools()
    tools.value = data.tools || []
  } catch (e: any) {
    error.value = e.message || '加载工具列表失败'
  } finally {
    loading.value = false
  }
})

function goToTool(toolId: string) {
  router.push(`/tool/${toolId}`)
}

async function onCleanupFiles() {
  if (!window.confirm('确认删除 uploads 目录下所有上传/生成的文件？')) return
  cleanupLoading.value = true
  cleanupMsg.value = ''
  try {
    const r = await cleanupUploadFiles()
    cleanupMsg.value = r.message || '清理完成'
  } catch (e: any) {
    cleanupMsg.value = e.message || '清理失败'
  } finally {
    cleanupLoading.value = false
  }
}
</script>

<template>
  <div class="main-page">
    <header class="page-header">
      <h1>工具中心</h1>
      <p class="subtitle">集成多个业务工具，选择工具开始使用</p>
      <button class="btn-cleanup" :disabled="cleanupLoading" @click="onCleanupFiles">
        {{ cleanupLoading ? '清理中...' : '🗑 清理上传文件' }}
      </button>
      <span v-if="cleanupMsg" class="cleanup-msg">{{ cleanupMsg }}</span>
    </header>

    <div v-if="loading" class="status-msg">加载工具列表中...</div>
    <div v-else-if="error" class="status-msg error">{{ error }}</div>
    <div v-else-if="tools.length === 0" class="status-msg">暂无可用工具</div>

    <main v-else class="tool-grid">
      <button
        v-for="tool in tools"
        :key="tool.tool_id"
        class="tool-card"
        @click="goToTool(tool.tool_id)"
      >
        <h2>{{ tool.tool_name }}</h2>
        <p>{{ tool.description }}</p>
      </button>
    </main>
  </div>
</template>

<style scoped>
.main-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.btn-cleanup {
  padding: 6px 14px;
  border: 1px solid #ef9a9a;
  border-radius: 4px;
  background: #ffebee;
  color: #c62828;
  cursor: pointer;
  font-size: 13px;
  margin-top: 12px;
}

.btn-cleanup:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cleanup:hover:not(:disabled) {
  background: #ffcdd2;
}

.cleanup-msg {
  display: block;
  font-size: 12px;
  color: #e65100;
  margin-top: 6px;
}

.page-header h1 {
  font-size: 32px;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.subtitle {
  color: #888;
  font-size: 16px;
}

.status-msg {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 15px;
}

.status-msg.error {
  color: #c62828;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.tool-card {
  display: block;
  width: 100%;
  padding: 24px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.tool-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #1976d2;
}

.tool-card h2 {
  font-size: 18px;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.tool-card p {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}
</style>
