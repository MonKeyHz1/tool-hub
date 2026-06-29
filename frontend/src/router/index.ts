/**
 * Vue Router 配置 - 工具中心多页面路由。
 *
 * 每个工具拥有独立页面：
 * - /              : 主页面（工具按钮导航）
 * - /tool/:toolId  : 工具详情页
 */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/MainPage.vue'),
    },
    {
      path: '/tool/mip_customs_clearance',
      name: 'MIPCustoms',
      component: () => import('../views/MIPCustomsPage.vue'),
    },
    {
      path: '/tool/temu_gateway',
      name: 'TemuGateway',
      component: () => import('../views/TemuGatewayPage.vue'),
    },
    {
      path: '/tool/pdd_order',
      name: 'PDDOrder',
      component: () => import('../views/PDDOrderPage.vue'),
    },
    {
      path: '/tool/encoding_converter',
      name: 'EncodingConverter',
      component: () => import('../views/EncodingConverterPage.vue'),
    },
    {
      path: '/tool/push_weight',
      name: 'PushWeight',
      component: () => import('../views/PushWeightPage.vue'),
    },
    {
      path: '/tool/financial_system',
      name: 'FinancialSystem',
      component: () => import('../views/FinancialSystemPage.vue'),
    },
  ],
})

export default router
