<script setup lang="ts">
/**
 * EncodingConverterPage - 编码转换工具页面。
 *
 * 上传文件 → 检测编码 → 选择目标编码 → 下载转换后的文件。
 * 使用通用 ToolPanel 组件。
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchToolDetail } from '../api'
import ToolPanel from '../components/ToolPanel.vue'

const router = useRouter()
const toolId = 'encoding_converter'
const tool = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    tool.value = await fetchToolDetail(toolId)
  } catch (e) {
    console.error('加载工具详情失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="tool-page">
    <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
    <div v-if="loading" class="status-msg">加载工具中...</div>
    <ToolPanel v-else-if="tool" :tool="tool" />
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

.status-msg {
  text-align: center;
  padding: 40px;
  color: #666;
}

.status-msg.error {
  color: #c62828;
}
</style>
