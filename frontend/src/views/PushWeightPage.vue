<script setup lang="ts">
/**
 * PushWeightPage - 推送重量工具页面。
 *
 * 功能:
 * 1. 粘贴批量快递单号 → 查询获取尾程单号 + 出库通知状态
 * 2. 确认弹窗后推送重量到 TMS 生产环境
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { pushWeightQuery, pushWeightPush, fetchToolState } from '../api'

const router = useRouter()

// ================================================================
// 状态
// ================================================================

const inputText = ref('')
const queryLoading = ref(false)
const queryResult = ref<any>(null)
const queryError = ref('')

const pushLoading = ref(false)
const pushResult = ref<any>(null)
const pushError = ref('')

// ================================================================
// 方法
// ================================================================

/** 加载上次保存的输入 */
onMounted(async () => {
  try {
    const res = await fetchToolState('push_weight')
    if (res?.data?.last_input) {
      inputText.value = res.data.last_input
    }
  } catch {
    // 忽略
  }
})

/** 查询 */
async function onQuery() {
  const lines = inputText.value.split(/[\n,，\s]+/).filter(Boolean)
  if (!lines.length) {
    queryError.value = '请输入快递单号'
    return
  }
  queryLoading.value = true
  queryError.value = ''
  queryResult.value = null
  pushResult.value = null
  try {
    const res = await pushWeightQuery(lines)
    queryResult.value = res
  } catch (e: any) {
    queryError.value = e.response?.data?.message || e.message || '查询失败'
  } finally {
    queryLoading.value = false
  }
}

/** 获取可推送的尾程单号（排除已有出库通知的） */
function getPushableNumbers(): string[] {
  if (!queryResult.value?.data) return []
  return queryResult.value.data
    .filter((r: any) => r.ky_in_storage_number && !r.has_outbound_notice)
    .map((r: any) => r.ky_in_storage_number)
}

/** 推送（带确认） */
async function onPush() {
  const numbers = getPushableNumbers()
  if (!numbers.length) {
    pushError.value = '没有需要推送的尾程单号'
    return
  }

  // 确认弹窗
  const confirmed = window.confirm(
    `是否确认推送，该数据会推送PDD生产，请确认\n\n共 ${numbers.length} 条尾程单号`
  )
  if (!confirmed) return

  pushLoading.value = true
  pushError.value = ''
  pushResult.value = null
  try {
    const res = await pushWeightPush(numbers)
    pushResult.value = res
  } catch (e: any) {
    pushError.value = e.response?.data?.message || e.message || '推送失败'
  } finally {
    pushLoading.value = false
  }
}
</script>

<template>
  <div class="pw-page">
    <div class="top-bar">
      <button class="back-btn" @click="router.push('/')">← 返回工具列表</button>
      <h1>推送重量</h1>
      <span class="env-warn">⚠ 生产环境，谨慎操作</span>
    </div>

    <!-- 输入区 -->
    <div class="panel">
      <h3>快递单号</h3>
      <p class="desc">查询: POST /api/push-weight/query（查生产库 customer_order + outbound_notice_mail_detail）</p>
      <p class="desc">推送: POST /api/push-weight/push → GET /demo/pushPddOrderCrossLine（TMS生产）</p>
      <textarea
        v-model="inputText"
        rows="8"
        class="input number-input"
        placeholder="9817225664288&#10;9817225661224&#10;9817225661159"
      ></textarea>

      <div class="btn-row">
        <button class="btn btn-primary" :disabled="queryLoading" @click="onQuery">
          {{ queryLoading ? '查询中...' : '查询' }}
        </button>
      </div>

      <div v-if="queryError" class="error-box">{{ queryError }}</div>

      <!-- 查询结果 -->
      <div v-if="queryResult?.data" class="result-box">
        <h4>
          查询结果: 共 {{ queryResult.total }} 条，
          在库 {{ queryResult.found_in_db }} 条
          <span v-if="queryResult.not_found_in_db" class="warn-tag">
            ，未找到 {{ queryResult.not_found_in_db }} 条
          </span>
        </h4>

        <table class="data-table">
          <thead>
            <tr>
              <th>快递单号</th>
              <th>订单号</th>
              <th>尾程单号</th>
              <th>实重(kg)</th>
              <th>出库通知</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in queryResult.data" :key="i" :class="{ 'row-missing': !r.found_in_db }">
              <td><code>{{ r.tracking_number }}</code></td>
              <td>{{ r.order_number || '—' }}</td>
              <td><code>{{ r.ky_in_storage_number || '—' }}</code></td>
              <td>{{ r.reality_cross_weight ?? '—' }}</td>
              <td>
                <span v-if="!r.found_in_db" class="tag-missing">未找到</span>
                <span v-else-if="r.has_outbound_notice" class="tag-ok">已有</span>
                <span v-else class="tag-need">待推送</span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 未找到提示 -->
        <div v-if="queryResult.missing_numbers?.length" class="missing-box">
          <strong>以下单号未在数据库找到:</strong>
          {{ queryResult.missing_numbers.join(', ') }}
        </div>

        <!-- 推送按钮 -->
        <div v-if="getPushableNumbers().length" class="push-area">
          <p class="push-hint">待推送尾程单号: <strong>{{ getPushableNumbers().length }}</strong> 条</p>
          <button class="btn btn-danger" :disabled="pushLoading" @click="onPush">
            {{ pushLoading ? '推送中...' : '⚠ 推送到PDD生产' }}
          </button>
        </div>
      </div>

      <!-- 推送结果 -->
      <div v-if="pushResult" class="result-box push-result">
        <h4>
          推送结果:
          <span :class="pushResult.success ? 'success-tag' : 'fail-tag'">
            {{ pushResult.success ? '全部成功' : '部分失败' }}
          </span>
        </h4>
        <p>成功 {{ pushResult.success_count }}/{{ pushResult.total }}，
           失败 {{ pushResult.failed_count }}/{{ pushResult.total }}</p>
        <div v-if="pushResult.failed_list?.length" class="failed-list">
          <strong>失败明细:</strong>
          <div v-for="(f, i) in pushResult.failed_list" :key="i" class="kv">
            <code>{{ f.number }}</code>: {{ f.error || JSON.stringify(f.result) }}
          </div>
        </div>
      </div>

      <div v-if="pushError" class="error-box">{{ pushError }}</div>
    </div>
  </div>
</template>

<style scoped>
.pw-page {
  max-width: 1100px;
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

.env-warn {
  color: #e65100;
  font-size: 13px;
  font-weight: bold;
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
  margin: 0 0 16px 0;
}

.number-input {
  width: 100%;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}

.btn-row {
  margin-top: 12px;
}

.btn {
  padding: 8px 24px;
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
  background: #1976d2;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-danger {
  background: #d32f2f;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #b71c1c;
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
  margin-top: 16px;
  padding: 14px;
  background: #f5f5f5;
  border-radius: 6px;
}

.result-box h4 {
  margin: 0 0 8px 0;
  font-size: 15px;
}

.warn-tag {
  color: #e65100;
  font-weight: normal;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 6px 10px;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

.data-table th {
  background: #fafafa;
  color: #666;
  font-weight: 600;
}

.data-table code {
  background: #e8e8e8;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.row-missing {
  background: #fff3e0;
}

.tag-ok {
  color: #2e7d32;
  font-weight: bold;
}

.tag-need {
  color: #e65100;
  font-weight: bold;
}

.tag-missing {
  color: #c62828;
}

.missing-box {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fff3e0;
  border: 1px solid #ffe0b2;
  border-radius: 4px;
  font-size: 12px;
  color: #e65100;
}

.push-area {
  margin-top: 16px;
  padding: 14px;
  background: #fbe9e7;
  border: 1px solid #ffab91;
  border-radius: 6px;
}

.push-hint {
  font-size: 14px;
  margin: 0 0 10px 0;
}

.push-result {
  margin-top: 16px;
}

.success-tag {
  color: #2e7d32;
}

.fail-tag {
  color: #c62828;
}

.failed-list {
  margin-top: 10px;
}

.failed-list .kv {
  font-size: 13px;
  margin-bottom: 4px;
}

.kv code {
  background: #e8e8e8;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
}
</style>
