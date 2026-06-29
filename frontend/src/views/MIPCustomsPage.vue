<script setup lang="ts">
/**
 * MIPCustomsPage - MIP海关清关工具页。
 *
 * Tab 切换创建/更新模式，每 Tab 独立上传执行。顶部共享清状态按钮。
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { mipClearState } from '../api'
import MIPImportTab from '../components/MIPImportTab.vue'

const router = useRouter()

const activeTab = ref<'create' | 'update'>('create')
const clearLoading = ref(false)
const clearMsg = ref('')

async function onClearState() {
  if (!window.confirm('确认清除导入状态记录？')) return
  clearLoading.value = true
  clearMsg.value = ''
  try {
    const res = await mipClearState()
    clearMsg.value = res.message || '已清除'
  } catch (e: any) {
    clearMsg.value = e.message || '清除失败'
  } finally {
    clearLoading.value = false
  }
}
</script>

<template>
  <div class="mip-page">
  <div class="top-bar">
    <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
    <h1>MIP海关清关</h1>
    <span v-if="clearMsg" class="clear-msg">{{ clearMsg }}</span>
  </div>

  <div class="tabs">
    <button :class="['tab', { active: activeTab === 'create' }]" @click="activeTab = 'create'">
      创建 (POST)
    </button>
    <button :class="['tab', { active: activeTab === 'update' }]" @click="activeTab = 'update'">
      更新 (PUT)
    </button>
  </div>

  <MIPImportTab v-show="activeTab === 'create'" tool-id="mip_customs_create" title="创建" :use-create="true" @clear-state="onClearState" />
  <MIPImportTab v-show="activeTab === 'update'" tool-id="mip_customs_update" title="更新" :use-create="false" @clear-state="onClearState" />
  </div>
</template>

<style scoped>
.mip-page { max-width: 900px; margin: 0 auto; padding: 24px 16px; }

.top-bar { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }
.top-bar h1 { margin: 0; font-size: 24px; flex: 1; }

.back-btn { padding: 6px 16px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 14px; }
.back-btn:hover { background: #f5f5f5; }

.btn-clear { padding: 6px 16px; border: 1px solid #ef9a9a; border-radius: 4px; background: #ffebee; color: #c62828; cursor: pointer; font-size: 13px; }

.clear-msg { font-size: 12px; color: #e65100; margin-left: 4px; }

.tabs { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; }
.tab { padding: 10px 24px; border: none; background: none; cursor: pointer; font-size: 15px; color: #666; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab:hover { color: #1976d2; }
.tab.active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 600; }
</style>
