<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { pddCreateOrder, pddGetConfig, pddTmsLogin, pddInbound, pddAutoWeigh, pddManualWeigh,
  pddShelf, pddUnpack, pddOutbound, pddBag, pddVehicle, pddDispatch, pddRouteNodes, pddRoute, fetchToolState } from '../api'

const router = useRouter()
const configAppId = ref(''), configGatewayUrl = ref(''), configWarehouseCode = ref('')
const activeTab = ref('order')

const deliveryType = ref('homeDelivery')

const HOME_TEMPLATE = {
  providerCode:'KIMIGO_MN',consoWarehouseCode:'KIMIGO',bizType:'CONSO',consoType:'DIRECT_MAIL_DIRECT_ROAD',
  deliveryType:'homeDelivery',packageQuantity:1,
  items:[{itemId:'428743492117',itemName:'闹钟手表',categoryId:'8653',categoryName:'国产腕表',
    totalActualPayment:2990,currencyUnit:'CENT',currency:'CNY',itemQuantity:1,
    itemPicUrl:'https://img.pddpic.com/mms-material-img/2022-11-05/3d1e7fa4-3633-4e67-8508-b95d27c6d3e2.jpeg.a.jpeg',
    itemSkuProperty:'黑色太空人',goodsType:'SPECIAL'}],
  buyerDetail:{name:'Sarangoo Ganbold',telePhone:'95948917',country:'MN',province:'Darhan',city:'Darhan',
    district:'8-r bag',postCode:'45043',detailAddress:'Mikr 16-r bair 63toot'},
  stationCode:'UB-A-0002',mailDetails:[{expressCode:'SF',mailNo:'',tmsMark:0}],
  logisticsOrderCode:'',buyerCode:'',dereRecogCode:'',
  paymentDetail:{tradeOrderSn:'',tradeOrderValue:2990,tradeOrderActualAmount:2990,currencyUnit:'CENT',currency:'CNY'}
}
const PICKUP_TEMPLATE = {
  providerCode:'KIMIGO_MN',consoWarehouseCode:'KIMIGO',bizType:'CONSO',consoType:'DIRECT_MAIL_DIRECT_ROAD',
  deliveryType:'selfPickup',packageQuantity:1,
  items:[{itemId:'723443740193',itemName:'夏季连衣裙珍珠腰带',categoryId:'8718',categoryName:'腰带',
    totalActualPayment:550,currencyUnit:'CENT',currency:'CNY',itemQuantity:1,
    itemPicUrl:'https://img.pddpic.com/mms-material-img/2025-03-27/662252d9-d478-45c2-9795-e84dc0ee20c1.jpeg',
    itemSkuProperty:'款式3',chargedStatus:false,magneticStatus:false,goodsType:'SPECIAL'}],
  buyerDetail:{name:'Халиунаа',telePhone:'95010169',country:'MN',province:'Улаанбаатар хот',
    city:'Хан-Уул дүүрэг',district:'23-р хороо',detailAddress:'Ирээдүйн билэг хотхон б блок 5 давхар 20тоот',
    postCode:'17230',town:'',door:0},
  stationCode:'UB-A-0002',mailDetails:[{expressCode:'JT',mailNo:'',tmsMark:0}],
  logisticsOrderCode:'',buyerCode:'',dereRecogCode:'',
  paymentDetail:{tradeOrderSn:'',tradeOrderValue:550,tradeOrderActualAmount:550,currencyUnit:'CENT',currency:'CNY'},tags:['FREE_SHIPPING','AUTO_PACK'],totalPrice:''
}

const homeJson = ref(JSON.stringify(HOME_TEMPLATE, null, 2))
const pickupJson = ref(JSON.stringify(PICKUP_TEMPLATE, null, 2))
const orderJson = computed({ get:()=>deliveryType.value==='homeDelivery'?homeJson.value:pickupJson.value, set:(v)=>{ if(deliveryType.value==='homeDelivery')homeJson.value=v; else pickupJson.value=v }})
const orderLoading = ref(false), orderResult = ref<any>(null), orderError = ref('')
const autoInbound = ref(true), autoWeighFlow = ref(true), autoShelfFlow = ref(true)
const autoUnpackFlow = ref(true), autoOutboundFlow = ref(true), autoBagFlow = ref(true), autoVehicleFlow = ref(true)
const isPickup = computed(() => deliveryType.value !== 'homeDelivery')

watch(deliveryType, (val) => {
  if(val !== 'homeDelivery'){
    autoShelfFlow.value = false
    autoUnpackFlow.value = false
  }
})

const flowSteps = ref<{key:string,label:string,status:string}[]>([
  {key:'inbound',label:'入库',status:'pending'},{key:'weigh',label:'称重',status:'pending'},
  {key:'shelf',label:'上架',status:'pending'},{key:'unpack',label:'拆包',status:'pending'},
  {key:'outbound',label:'出库通知',status:'pending'},{key:'bag',label:'集包',status:'pending'},
  {key:'vehicle',label:'装车',status:'pending'},
])
function resetFlowSteps(){ flowSteps.value.forEach(s=>s.status='pending') }
function setStep(k:string,s:string){ const x=flowSteps.value.find(y=>y.key===k); if(x)x.status=s }

const tmsJobNumber = ref(''), tmsPassword = ref(''), tmsToken = ref('')
const loginLoading = ref(false), loginError = ref('')

const trackingNumber = ref(''), inboundLoading = ref(false), inboundResult = ref<any>(null), inboundError = ref('')

const weighTrackcode = ref(''), weighOrderNumber = ref(''), weighTrackingNumber = ref('')
const weighLength = ref('20.5'), weighWidth = ref('15.0'), weighHeight = ref('10.0'), weighWeight = ref('1.25')
const autoWeighLoading = ref(false), autoWeighResult = ref<any>(null), autoWeighError = ref('')
const manualWeighLoading = ref(false), manualWeighResult = ref<any>(null), manualWeighError = ref('')

const shelfTrackingNumber = ref(''), shelfWarehouseCode = ref('langfang_warehouse_1'), shelfBinCode = ref('A1-1-2')
const shelfLoading = ref(false), shelfResult = ref<any>(null), shelfError = ref('')

const unpackOrderCode = ref(''), unpackBuyerCode = ref(''), unpackMailNo = ref(''), unpackDeliveryType = ref('homeDelivery')
const unpackReceiverName = ref(''), unpackReceiverPhone = ref('')
const unpackReceiverProvince = ref(''), unpackReceiverCity = ref(''), unpackReceiverDistrict = ref('')
const unpackReceiverAddress = ref(''), unpackReceiverPostCode = ref('')
const unpackLoading = ref(false), unpackResult = ref<any>(null), unpackError = ref('')

const outboundOrderCode = ref(''), outboundBuyerCode = ref(''), outboundMailNo = ref('')
const outboundTradeOrderSn = ref(''), outboundDeliveryType = ref('homeDelivery')
const outboundReceiverName = ref(''), outboundReceiverPhone = ref(''), outboundWeight = ref(1250)
const outboundLoading = ref(false), outboundResult = ref<any>(null), outboundError = ref('')

const bagPpCode = ref(''), bagMailNos = ref(''), bagOutboundType = ref(1)
const bagLoading = ref(false), bagResult = ref<any>(null), bagError = ref('')

const vehicleBagNos = ref(''), vehicleLoading = ref(false), vehicleResult = ref<any>(null), vehicleError = ref('')
const dispatchLoading = ref(false), dispatchResult = ref<any>(null)

const batchOrderCount = ref('3'), batchPickupCount = ref('0'), batchBagSize = ref('3'), batchBinCode = ref('A1-1-2'), batchStepInterval = ref('0')
const batchSteps = ref<string[]>(['inbound','weigh','shelf','unpack','outbound','bag','vehicle','dispatch'])
const batchLoading = ref(false), batchProgress = ref<string[]>([]), batchStepStates = ref<Record<string,string>>({})
const batchOrders = ref<any[]>([]), batchResult = ref<any>(null), batchError = ref('')
const batchWarehouseCode = ref('langfang_warehouse_1')
const batchRouteIds = ref<number[]>([])
const batchFailNodeId = ref<number>(0)

const ROUTE_ORDER_MAP: Record<number,number> = {224:1,165:2,166:3,167:4,168:5,169:6,170:7,171:8,176:9,172:10,219:11,174:11,209:12,173:12,175:12}
function routeSort(a:{id:number,name:string},b:{id:number,name:string}){ return (ROUTE_ORDER_MAP[a.id]||999) - (ROUTE_ORDER_MAP[b.id]||999) || a.id-b.id }

// --- 物流轨迹 ---
const routeNodes = ref<{normal:{id:number,name:string}[],fail:{id:number,name:string}[]}>({normal:[],fail:[]})
const routeNodeId = ref<number>(168)
const routeVehicleId = ref<number>(0)
const routeBillNo = ref('')
const routeLoading = ref(false)
const routeResult = ref<any>(null)
const routeError = ref('')

onMounted(async ()=>{ loadConfig(); loadState(); loadRouteNodes() })

async function loadRouteNodes(){
  try{ const r = await pddRouteNodes(); routeNodes.value = r || {normal:[],fail:[]} } catch {}
}

async function onRoute(){
  routeLoading.value=true; routeError.value=''; routeResult.value=null
  try{
    const r=await pddRoute(tmsToken.value, routeVehicleId.value, routeNodeId.value, routeBillNo.value)
    routeResult.value=r
  }catch(e:any){routeError.value=e.message||'fail'}finally{routeLoading.value=false}
}

async function loadConfig(){ try{ const r=await pddGetConfig(); configAppId.value=r.app_id; configGatewayUrl.value=r.gateway_url; configWarehouseCode.value=r.warehouse_code } catch{} }
onMounted(()=>{ loadConfig(); loadState() })

async function loadState(){
  try{const r=await fetchToolState('pdd_order');const s=r?.data;if(!s)return
  if(s.delivery_type)deliveryType.value=s.delivery_type; if(s.home_json){try{homeJson.value=JSON.stringify(JSON.parse(s.home_json),null,2)}catch{homeJson.value=s.home_json}}; if(s.pickup_json){try{pickupJson.value=JSON.stringify(JSON.parse(s.pickup_json),null,2)}catch{pickupJson.value=s.pickup_json}}; if(s.order_json&&!s.home_json){try{homeJson.value=JSON.stringify(JSON.parse(s.order_json),null,2)}catch{homeJson.value=s.order_json}}
  if(s.tms_job_number)tmsJobNumber.value=s.tms_job_number; if(s.tms_password)tmsPassword.value=s.tms_password
  if(s.tms_token)tmsToken.value=s.tms_token; if(s.inbound_tracking_number)trackingNumber.value=s.inbound_tracking_number
  if(s.weigh_trackcode)weighTrackcode.value=s.weigh_trackcode; if(s.weigh_order_number)weighOrderNumber.value=s.weigh_order_number
  if(s.weigh_tracking_number)weighTrackingNumber.value=s.weigh_tracking_number; if(s.weigh_length)weighLength.value=s.weigh_length
  if(s.weigh_width)weighWidth.value=s.weigh_width; if(s.weigh_height)weighHeight.value=s.weigh_height; if(s.weigh_weight)weighWeight.value=s.weigh_weight
  if(s.shelf_tracking_number)shelfTrackingNumber.value=s.shelf_tracking_number; if(s.shelf_warehouse_code)shelfWarehouseCode.value=s.shelf_warehouse_code
  if(s.shelf_bin_code)shelfBinCode.value=s.shelf_bin_code; if(s.unpack_logistics_order_code)unpackOrderCode.value=s.unpack_logistics_order_code
  if(s.outbound_logistics_order_code)outboundOrderCode.value=s.outbound_logistics_order_code
  if(s.batch_bin_code)batchBinCode.value=s.batch_bin_code; if(s.batch_home_count)batchOrderCount.value=s.batch_home_count
  if(s.batch_pickup_count)batchPickupCount.value=s.batch_pickup_count; if(s.batch_bag_size)batchBagSize.value=s.batch_bag_size
  if(s.batch_step_interval)batchStepInterval.value=s.batch_step_interval
  }catch{}
}

async function onTmsLogin(){ loginLoading.value=true; loginError.value=''
  try{const r=await pddTmsLogin(tmsJobNumber.value,tmsPassword.value);if(r.success)tmsToken.value=r.token;else loginError.value=r.message||'login fail'}
  catch(e:any){loginError.value=e.message||'login fail'}finally{loginLoading.value=false}}

async function onCreateOrder(){ orderLoading.value=true;orderError.value='';orderResult.value=null
  try{
    const body=JSON.parse(orderJson.value);const r=await pddCreateOrder(deliveryType.value,body);orderResult.value=r
    if(r.success&&r.sent_mail_no){
      weighTrackcode.value=r.sent_mail_no;weighOrderNumber.value=r.sent_logistics_order_code||''
      weighTrackingNumber.value=r.sent_mail_no;shelfTrackingNumber.value=r.sent_mail_no
      trackingNumber.value=r.sent_mail_no;unpackOrderCode.value=r.sent_logistics_order_code||''
      unpackBuyerCode.value=r.sent_buyer_code||'';unpackMailNo.value=r.sent_mail_no
      outboundOrderCode.value=r.sent_logistics_order_code||'';outboundBuyerCode.value=r.sent_buyer_code||''
      outboundMailNo.value=r.sent_mail_no;outboundTradeOrderSn.value=r.sent_trade_order_sn||'';outboundDeliveryType.value=deliveryType.value;bagMailNos.value=r.sent_mail_no
      bagOutboundType.value=deliveryType.value==='homeDelivery'?1:0
      const pc=r.sent_logistics_order_code||'';bagPpCode.value=deliveryType.value==='homeDelivery'?pc.replace('PC','PP'):pc
      try{const ob=JSON.parse(orderJson.value);const bd=ob.buyerDetail||{};
        unpackReceiverName.value=bd.name||'';unpackReceiverPhone.value=bd.telePhone||''
        unpackReceiverProvince.value=bd.province||'';unpackReceiverCity.value=bd.city||''
        unpackReceiverDistrict.value=bd.district||'';unpackReceiverAddress.value=bd.detailAddress||''
        unpackReceiverPostCode.value=bd.postCode||'';outboundReceiverName.value=bd.name||'';outboundReceiverPhone.value=bd.telePhone||''}catch{}
    }
    if(r.success&&r.sent_mail_no){
      const steps=[
        {key:'inbound',label:'入库',needToken:true},
        {key:'weigh',label:'称重',needToken:false},
        {key:'shelf',label:'上架',needToken:true},
        {key:'unpack',label:'拆包',needToken:false},
        {key:'outbound',label:'出库通知',needToken:false},
        {key:'bag',label:'集包',needToken:true},
        {key:'vehicle',label:'装车',needToken:true},
      ]
      const enabled = steps.filter(s => {
        const chk = (s.key==='inbound' && autoInbound.value) ||
             (s.key==='weigh' && autoWeighFlow.value) ||
             (s.key==='shelf' && autoShelfFlow.value) ||
             (s.key==='unpack' && autoUnpackFlow.value) ||
             (s.key==='outbound' && autoOutboundFlow.value) ||
             (s.key==='bag' && autoBagFlow.value) ||
             (s.key==='vehicle' && autoVehicleFlow.value)
        return chk
      })
      if(enabled.length){
        resetFlowSteps(); await new Promise(rr=>setTimeout(rr,1000))
        for(const step of enabled){
          setStep(step.key,'loading')
          // 需要 token 但未登录 → 自动登录
          if(step.needToken && !tmsToken.value){
            if(tmsJobNumber.value && tmsPassword.value){
              await onTmsLogin()
              if(!tmsToken.value){ setStep(step.key,'fail'); break }
            }else{
              setStep(step.key,'fail'); break
            }
          }
          try{let ok=false
            if(step.key==='inbound'){await onInbound();ok=inboundResult.value?.success}
            else if(step.key==='weigh'){await onAutoWeigh();ok=autoWeighResult.value?.success}
            else if(step.key==='shelf'){await onShelf();ok=shelfResult.value?.success}
            else if(step.key==='unpack'){await onUnpack();ok=unpackResult.value?.success;if(ok&&unpackResult.value?.pp_code){outboundOrderCode.value=unpackResult.value.pp_code;bagPpCode.value=unpackResult.value.pp_code}}
            else if(step.key==='outbound'){await onOutbound();ok=outboundResult.value?.success;if(ok&&unpackResult.value?.pp_code)bagPpCode.value=unpackResult.value.pp_code}
            else if(step.key==='bag'){await onBag();ok=bagResult.value?.success;if(ok&&bagResult.value?.data?.bag_no)vehicleBagNos.value=bagResult.value.data.bag_no}
            else if(step.key==='vehicle'){await onVehicle();ok=vehicleResult.value?.success}
            setStep(step.key,ok?'done':'fail');if(!ok)break
          }catch{setStep(step.key,'fail');break}
        }
      }
    }
  }catch(e:any){orderError.value=e.response?.data?.message||e.message||'fail'}finally{orderLoading.value=false}}

async function onInbound(){ inboundLoading.value=true;inboundError.value='';inboundResult.value=null
  try{const r=await pddInbound(tmsToken.value,trackingNumber.value);inboundResult.value=r}catch(e:any){inboundError.value=e.message||'fail'}finally{inboundLoading.value=false}}
async function onAutoWeigh(){ autoWeighLoading.value=true;autoWeighError.value='';autoWeighResult.value=null
  try{const r=await pddAutoWeigh(weighTrackcode.value,+weighLength.value,+weighWidth.value,+weighHeight.value,+weighWeight.value);autoWeighResult.value=r}catch(e:any){autoWeighError.value=e.message||'fail'}finally{autoWeighLoading.value=false}}
async function onManualWeigh(){ manualWeighLoading.value=true;manualWeighError.value='';manualWeighResult.value=null
  try{const r=await pddManualWeigh(tmsToken.value,weighOrderNumber.value,weighTrackingNumber.value,+weighLength.value,+weighWidth.value,+weighHeight.value,+weighWeight.value);manualWeighResult.value=r}catch(e:any){manualWeighError.value=e.message||'fail'}finally{manualWeighLoading.value=false}}
async function onShelf(){ shelfLoading.value=true;shelfError.value='';shelfResult.value=null
  try{const r=await pddShelf(tmsToken.value,shelfTrackingNumber.value,shelfWarehouseCode.value,shelfBinCode.value);shelfResult.value=r}catch(e:any){shelfError.value=e.message||'fail'}finally{shelfLoading.value=false}}
async function onUnpack(){ unpackLoading.value=true;unpackError.value='';unpackResult.value=null
  try{const r=await pddUnpack(unpackOrderCode.value,unpackBuyerCode.value,unpackMailNo.value,unpackDeliveryType.value,{name:unpackReceiverName.value,telePhone:unpackReceiverPhone.value,country:'MN',province:unpackReceiverProvince.value,city:unpackReceiverCity.value,district:unpackReceiverDistrict.value,detailAddress:unpackReceiverAddress.value,postCode:unpackReceiverPostCode.value});unpackResult.value=r;if(r.success&&r.pp_code){outboundOrderCode.value=r.pp_code;bagPpCode.value=r.pp_code}}catch(e:any){unpackError.value=e.message||'fail'}finally{unpackLoading.value=false}}
async function onOutbound(){ outboundLoading.value=true;outboundError.value='';outboundResult.value=null
  try{let items:any[]=[];try{items=JSON.parse(orderJson.value).items||[]}catch{};const r=await pddOutbound(outboundOrderCode.value,outboundBuyerCode.value,outboundMailNo.value,outboundTradeOrderSn.value,outboundDeliveryType.value,items,{name:outboundReceiverName.value,telePhone:outboundReceiverPhone.value,country:'MN',province:unpackReceiverProvince.value,city:unpackReceiverCity.value,district:unpackReceiverDistrict.value,detailAddress:unpackReceiverAddress.value,postCode:unpackReceiverPostCode.value},outboundWeight.value);outboundResult.value=r;if(r.success&&unpackResult.value?.pp_code)bagPpCode.value=unpackResult.value.pp_code}catch(e:any){outboundError.value=e.message||'fail'}finally{outboundLoading.value=false}}
async function onBag(){ bagLoading.value=true;bagError.value='';bagResult.value=null
  try{    const r=await pddBag(tmsToken.value,bagPpCode.value,bagMailNos.value,bagOutboundType.value);bagResult.value=r;if(r.success&&r.data?.bag_no)vehicleBagNos.value=r.data.bag_no}catch(e:any){bagError.value=e.message||'fail'}finally{bagLoading.value=false}}
async function onVehicle(){ vehicleLoading.value=true;vehicleError.value='';vehicleResult.value=null
  try{const r=await pddVehicle(tmsToken.value,vehicleBagNos.value);vehicleResult.value=r;if(r.success&&r.data?.vehicle_id){routeVehicleId.value=r.data.vehicle_id;routeBillNo.value=r.data.plate||''}}catch(e:any){vehicleError.value=e.message||'fail'}finally{vehicleLoading.value=false}}
async function onDispatch(){ dispatchLoading.value=true;dispatchResult.value=null
  try{const r=await pddDispatch(tmsToken.value,vehicleResult.value.data.vehicle_id);dispatchResult.value=r}catch(e:any){dispatchResult.value={success:false,message:e.message}}finally{dispatchLoading.value=false}}

function toggleBatchStep(step:string){ const idx=batchSteps.value.indexOf(step);if(idx>=0)batchSteps.value.splice(idx,1);else batchSteps.value.push(step)}
async function onBatch(){
  batchLoading.value=true;batchError.value='';batchProgress.value=[];batchStepStates.value={};batchOrders.value=[];batchResult.value=null
  try{
    const body=JSON.parse(orderJson.value)
    const resp=await fetch('/api/pdd-order/batch',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({home_count:+batchOrderCount.value,pickup_count:+batchPickupCount.value,bag_group_size:+batchBagSize.value,steps:batchSteps.value,delivery_type:deliveryType.value,token:tmsToken.value,warehouse_code:batchWarehouseCode.value,bin_code:batchBinCode.value,step_interval:parseFloat(batchStepInterval.value||'0'),route_ids:[...batchRouteIds.value,...(batchFailNodeId.value?[batchFailNodeId.value]:[])],order_body:JSON.parse(orderJson.value)})})
    const reader=resp.body!.getReader();const decoder=new TextDecoder();let buf=''
    while(true){const{value,done}=await reader.read();if(done)break;buf+=decoder.decode(value,{stream:true})
      const parts=buf.split('\n\n');buf=parts.pop()||''
      for(const p of parts){const lines=p.split('\n');let event='',data=''
        for(const l of lines){if(l.startsWith('event:'))event=l.slice(6).trim();else if(l.startsWith('data:'))data=l.slice(5).trim()}
        if(!event||!data)continue
        try{
          const d=JSON.parse(data)
          if(event==='step'){
            batchStepStates.value[d.key||d.step]=d.status
            batchProgress.value.push(`${d.status==='done'?'✓':d.status==='fail'?'X':'O'} ${d.step}: ${d.msg}`)
            if(d.errors){
              for(const e of d.errors){
                batchProgress.value.push(` ${e.mail_no}: ${JSON.stringify(e.body)}`)
              }
            }
          }else if(event==='progress'){
            if(d.msg){ batchProgress.value.push(d.msg) }
            else if(d.bag_no){ batchProgress.value.push(`包${d.idx}/${d.total}: ${d.bag_no} (${d.count||0}单)`) }
            else{ batchProgress.value.push(`${d.ok?'OK':'FAIL'} 下单${d.idx}/${d.total}: ${d.type==='pickup'?'[自提]':'[上门]'} ${d.mail_no}`) }
          }else if(event==='done'){
            batchOrders.value=d.orders||[]
            batchResult.value={data:{orders:d.orders,bags:d.bags,vehicle:d.vehicle}}
            batchProgress.value.push('done')
          }else if(event==='error'){
            batchError.value=d.message
            batchProgress.value.push(`ERROR: ${d.message}`)
            if(d.errors){
              for(const e of d.errors){
                batchProgress.value.push(` ${e.mail_no}: ${JSON.stringify(e.body)}`)
              }
            }
          }
        }catch{}
      }
    }
  }catch(e:any){
    batchError.value=e.message||'fail'
  }finally{
    batchLoading.value=false
  }
}
</script>

<template>
  <div class="pdd">
    <div class="tb"><button class="bk" @click="router.push('/')">back</button><h1>PDD-MN</h1></div>
    <div class="cfg"><span>appId: <strong>{{configAppId||'-'}}</strong></span><span>warehouse: <strong>{{configWarehouseCode||'-'}}</strong></span><span class="gw">gateway: {{configGatewayUrl||'-'}}</span></div>
    <div class="ts">
      <button v-for="t in ['order','inbound','weigh','shelf','unpack','outbound','bag','vehicle','batch','route']" :key="t" :class="['tb1',{act:activeTab===t}]" @click="activeTab=t">{{{order:'下单',inbound:'入库',weigh:'称重',shelf:'上架',unpack:'拆包',outbound:'出库通知',bag:'集包',vehicle:'装车',batch:'批量',route:'物流轨迹'}[t]}}</button>
    </div>

    <!-- order -->
    <div v-show="activeTab==='order'" class="pnl">
      <h3>下单</h3><p class="ds">POST /api/pdd/callback/conso/order/create</p>
      <div class="fr"><label>配送方式</label><select v-model="deliveryType" class="in"><option value="homeDelivery">上门</option><option value="selfPickup">自提</option></select></div>
      <div class="hb"><strong>自动生成字段:</strong><ul><li><code>logisticsOrderCode</code><span v-if="orderResult?.sent_logistics_order_code" class="gv">->{{orderResult.sent_logistics_order_code}}</span></li><li><code>buyerCode</code><span v-if="orderResult?.sent_buyer_code" class="gv">->{{orderResult.sent_buyer_code}}</span></li><li><code>dereRecogCode</code><span v-if="orderResult?.sent_dere_recog_code" class="gv">->{{orderResult.sent_dere_recog_code}}</span></li><li><code>tradeOrderSn</code><span v-if="orderResult?.sent_trade_order_sn" class="gv">->{{orderResult.sent_trade_order_sn}}</span></li><li><code>mailNo</code><span v-if="orderResult?.sent_mail_no" class="gv">->{{orderResult.sent_mail_no}}</span></li></ul><p v-if="orderResult?.sent_logistics_order_code" class="pp">PP码: <code>{{orderResult.sent_logistics_order_code.replace('PC','PP')}}</code></p></div>
      <div class="fr"><label>JSON</label><textarea v-model="orderJson" rows="16" class="in ji"></textarea></div>
      <button class="bt bt1" :disabled="orderLoading" @click="onCreateOrder">{{orderLoading?'提交中...':'创建订单'}}</button>
      <label class="ac"><input type="checkbox" v-model="autoInbound"/>入库</label>
      <label class="ac"><input type="checkbox" v-model="autoWeighFlow"/>称重</label>
      <label class="ac"><input type="checkbox" v-model="autoShelfFlow" :disabled="isPickup"/>上架</label>
      <label class="ac"><input type="checkbox" v-model="autoUnpackFlow" :disabled="isPickup"/>拆包</label>
      <label class="ac"><input type="checkbox" v-model="autoOutboundFlow"/>出库通知</label>
      <label class="ac"><input type="checkbox" v-model="autoBagFlow"/>集包</label>
      <label class="ac"><input type="checkbox" v-model="autoVehicleFlow"/>装车</label>
      <div v-if="flowSteps.some(s=>s.status!=='pending')" class="fb"><span v-for="s in flowSteps" :key="s.key" :class="['fs',s.status]"><span v-if="s.status==='loading'" class="sp"></span><span v-else-if="s.status==='done'">V</span><span v-else-if="s.status==='fail'">X</span><span v-else>O</span>{{s.label}}</span></div>
      <div v-if="orderError" class="er">{{orderError}}</div>
      <div v-if="orderResult" class="rb"><h4>结果: <span :class="orderResult.success?'ok':'fl'">{{orderResult.success?'成功':'失败'}}</span></h4>
        <div v-if="!orderResult.success" class="er">{{orderResult.data?.message||orderResult.data?.reason||JSON.stringify(orderResult.data)}}</div>
        <div v-if="orderResult.sent_logistics_order_code||orderResult.sent_mail_no" class="si">
          <div v-if="orderResult.sent_logistics_order_code" class="kv"><span>订单号:</span><code>{{orderResult.sent_logistics_order_code}}</code></div>
          <div v-if="orderResult.sent_mail_no" class="kv"><span>运单号:</span><code>{{orderResult.sent_mail_no}}</code></div>
          <div v-if="orderResult.sent_buyer_code" class="kv"><span>买家编码:</span><code>{{orderResult.sent_buyer_code}}</code></div>
          <div v-if="orderResult.sent_trade_order_sn" class="kv"><span>交易单号:</span><code>{{orderResult.sent_trade_order_sn}}</code></div></div>
        <pre class="jd">{{JSON.stringify(orderResult,null,2)}}</pre></div>
    </div>

    <!-- inbound -->
    <div v-show="activeTab==='inbound'" class="pnl"><h3>入库</h3><p class="ds">POST /api/Warehouse/CustomerOrderInStorage</p>
      <div class="fr"><label>工号</label><input v-model="tmsJobNumber" type="text" class="in"/></div>
      <div class="fr"><label>密码</label><input v-model="tmsPassword" type="password" class="in"/></div>
      <button class="bt bt2" :disabled="loginLoading" @click="onTmsLogin">{{loginLoading?'登录中...':'登录TMS'}}</button>
      <span v-if="tmsToken" class="to">已登录</span><div v-if="loginError" class="er">{{loginError}}</div>
      <div v-if="tmsToken" class="ia"><div class="fr"><label>运单号</label><input v-model="trackingNumber" type="text" class="in"/></div>
      <button class="bt bt1" :disabled="inboundLoading" @click="onInbound">{{inboundLoading?'入库中...':'入库'}}</button>
      <div v-if="inboundError" class="er">{{inboundError}}</div><div v-if="inboundResult" class="rb"><h4><span :class="inboundResult.success?'ok':'fl'">{{inboundResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(inboundResult.data,null,2)}}</pre></div></div>
    </div>

    <!-- weigh -->
    <div v-show="activeTab==='weigh'" class="pnl"><h3>称重</h3>
      <div class="fr"><label>长</label><input v-model="weighLength" type="number" step="0.1" class="in s"/><label>宽</label><input v-model="weighWidth" type="number" step="0.1" class="in s"/><label>高</label><input v-model="weighHeight" type="number" step="0.1" class="in s"/><label>重量</label><input v-model="weighWeight" type="number" step="0.01" class="in s"/></div>
      <div class="sb"><h4>自动</h4><p class="ds">POST /api/Equipment/SyncCrossLineData</p><div class="fr"><label>trackcode</label><input v-model="weighTrackcode" type="text" class="in"/></div><button class="bt bt1" :disabled="autoWeighLoading" @click="onAutoWeigh">{{autoWeighLoading?'称重中...':'自动称重'}}</button><div v-if="autoWeighError" class="er">{{autoWeighError}}</div><div v-if="autoWeighResult" class="rb"><h4><span :class="autoWeighResult.success?'ok':'fl'">{{autoWeighResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(autoWeighResult.data,null,2)}}</pre></div></div>
      <div class="sb"><h4>手动</h4><p class="ds">POST /api/CustomerOrderCaiNiaoKz/CaiNiaoKzOrderManualWeight</p><div class="fr"><label>订单号</label><input v-model="weighOrderNumber" type="text" class="in"/></div><div class="fr"><label>运单号</label><input v-model="weighTrackingNumber" type="text" class="in"/></div><button class="bt bt1" :disabled="manualWeighLoading||!tmsToken" @click="onManualWeigh">{{manualWeighLoading?'称重中...':'手动称重'}}</button><div v-if="manualWeighError" class="er">{{manualWeighError}}</div><div v-if="manualWeighResult" class="rb"><h4><span :class="manualWeighResult.success?'ok':'fl'">{{manualWeighResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(manualWeighResult.data,null,2)}}</pre></div></div>
    </div>

    <!-- shelf -->
    <div v-show="activeTab==='shelf'" class="pnl"><h3>上架</h3><p class="ds">POST /api/Warehouse/PutPackageOrderOnShelf</p>
      <div class="fr"><label>运单号</label><input v-model="shelfTrackingNumber" type="text" class="in"/></div>
      <div class="fr"><label>仓库</label><input v-model="shelfWarehouseCode" type="text" class="in"/></div>
      <div class="fr"><label>货架号</label><input v-model="shelfBinCode" type="text" class="in"/></div>
      <button class="bt bt1" :disabled="shelfLoading||!tmsToken" @click="onShelf">{{shelfLoading?'上架中...':'上架'}}</button>
      <div v-if="shelfError" class="er">{{shelfError}}</div><div v-if="shelfResult" class="rb"><h4><span :class="shelfResult.success?'ok':'fl'">{{shelfResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(shelfResult.data,null,2)}}</pre></div>
    </div>

    <!-- unpack -->
    <div v-show="activeTab==='unpack'" class="pnl"><h3>拆包通知</h3><p class="ds">POST /api/pdd/callback/conso/unpack/notice</p>
      <div class="fr"><label>订单号</label><input v-model="unpackOrderCode" type="text" class="in"/></div>
      <div class="fr"><label>买家编码</label><input v-model="unpackBuyerCode" type="text" class="in"/></div>
      <div class="fr"><label>运单号</label><input v-model="unpackMailNo" type="text" class="in"/></div>
      <div class="fr"><label>配送</label><select v-model="unpackDeliveryType" class="in"><option value="homeDelivery">上门</option><option value="selfPickup">自提</option></select></div>
      <div class="fr"><label>姓名</label><input v-model="unpackReceiverName" type="text" class="in s2"/><input v-model="unpackReceiverPhone" type="text" class="in s2" placeholder="电话"/></div>
      <div class="fr"><label>地址</label><input v-model="unpackReceiverProvince" type="text" class="in s2" placeholder="省"/><input v-model="unpackReceiverCity" type="text" class="in s2" placeholder="市"/><input v-model="unpackReceiverDistrict" type="text" class="in s2" placeholder="区"/></div>
      <div class="fr"><label></label><input v-model="unpackReceiverAddress" type="text" class="in" placeholder="详细地址"/></div>
      <div class="fr"><label>邮编</label><input v-model="unpackReceiverPostCode" type="text" class="in s2"/></div>
      <button class="bt bt1" :disabled="unpackLoading" @click="onUnpack">{{unpackLoading?'发送中...':'拆包通知'}}</button>
      <div v-if="unpackError" class="er">{{unpackError}}</div><div v-if="unpackResult" class="rb"><h4><span :class="unpackResult.success?'ok':'fl'">{{unpackResult.success?'成功':'失败'}}</span></h4><div v-if="unpackResult.pp_code" class="kv"><span>PP码:</span><code>{{unpackResult.pp_code}}</code></div><pre class="jd">{{JSON.stringify(unpackResult.data,null,2)}}</pre></div>
    </div>

    <!-- outbound -->
    <div v-show="activeTab==='outbound'" class="pnl"><h3>出库通知</h3><p class="ds">POST /api/pdd/callback/conso/outbound/notice</p>
      <div class="fr"><label>订单号</label><input v-model="outboundOrderCode" type="text" class="in"/></div>
      <div class="fr"><label>买家编码</label><input v-model="outboundBuyerCode" type="text" class="in"/></div>
      <div class="fr"><label>运单号</label><input v-model="outboundMailNo" type="text" class="in"/></div>
      <div class="fr"><label>交易单号</label><input v-model="outboundTradeOrderSn" type="text" class="in"/></div>
      <div class="fr"><label>重量(g)</label><input v-model.number="outboundWeight" type="number" class="in"/></div>
      <div class="fr"><label>配送</label><select v-model="outboundDeliveryType" class="in"><option value="homeDelivery">上门</option><option value="selfPickup">自提</option></select></div>
      <div class="fr"><label>姓名</label><input v-model="outboundReceiverName" type="text" class="in"/></div>
      <div class="fr"><label>电话</label><input v-model="outboundReceiverPhone" type="text" class="in"/></div>
      <button class="bt bt1" :disabled="outboundLoading" @click="onOutbound">{{outboundLoading?'发送中...':'出库通知'}}</button>
      <div v-if="outboundError" class="er">{{outboundError}}</div><div v-if="outboundResult" class="rb"><h4><span :class="outboundResult.success?'ok':'fl'">{{outboundResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(outboundResult.data,null,2)}}</pre></div>
    </div>

    <!-- bag -->
    <div v-show="activeTab==='bag'" class="pnl"><h3>集包</h3><p class="ds">POST /api/CustomerOutbound/AddPddEmptyCustomerOutBound -> PackageInStorge</p>
      <div class="fr"><label>code</label><input v-model="bagPpCode" type="text" class="in"/></div>
      <div class="fr"><label>运单号</label><input v-model="bagMailNos" type="text" class="in"/></div>
      <div class="fr"><label>类型</label><select v-model.number="bagOutboundType" class="in s2"><option :value="1">上门(1)</option><option :value="0">自提(0)</option></select></div>
      <button class="bt bt1" :disabled="bagLoading||!tmsToken" @click="onBag">{{bagLoading?'集包中...':'集包'}}</button>
      <div v-if="bagError" class="er">{{bagError}}</div><div v-if="bagResult" class="rb"><h4><span :class="bagResult.success?'ok':'fl'">{{bagResult.success?'成功':'失败'}}</span></h4><div class="er" v-if="!bagResult.success&&bagResult.message">{{bagResult.message}}</div><div v-if="bagResult.data?.bag_no" class="kv"><span>大包号:</span><code>{{bagResult.data.bag_no}}</code></div><div v-if="bagResult.data?.combined_nos" class="kv"><span>合单号:</span><code>{{bagResult.data.combined_nos}}</code></div><pre class="jd">{{JSON.stringify(bagResult,null,2)}}</pre></div>
    </div>

    <!-- vehicle -->
    <div v-show="activeTab==='vehicle'" class="pnl"><h3>装车</h3><p class="ds">POST AddAndUpdateProductPlanBillBasicV2 -> AddProductPlanBillBasicSend</p>
      <div class="fr"><label>包号</label><input v-model="vehicleBagNos" type="text" class="in"/></div>
      <button class="bt bt1" :disabled="vehicleLoading||!tmsToken" @click="onVehicle">{{vehicleLoading?'装车中...':'装车'}}</button>
      <button v-if="vehicleResult?.data?.vehicle_id" class="bt bt3" :disabled="dispatchLoading" @click="onDispatch">{{dispatchLoading?'发车中...':'发车'}}</button>
      <div v-if="vehicleError" class="er">{{vehicleError}}</div><div v-if="vehicleResult" class="rb"><h4><span :class="vehicleResult.success?'ok':'fl'">{{vehicleResult.success?'成功':'失败'}}</span></h4><div v-if="vehicleResult.data?.plate" class="kv"><span>车牌号:</span><code>{{vehicleResult.data.plate}}</code></div><pre class="jd">{{JSON.stringify(vehicleResult.data,null,2)}}</pre><div v-if="dispatchResult" class="dr"><h4>发车:<span :class="dispatchResult.success?'ok':'fl'">{{dispatchResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(dispatchResult.data,null,2)}}</pre></div></div>
    </div>

    <!-- batch -->
    <div v-show="activeTab==='batch'" class="pnl"><h3>批量</h3>
      <div class="fr"><label>上门</label><input v-model="batchOrderCount" type="number" min="0" class="in s"/><label>自提</label><input v-model="batchPickupCount" type="number" min="0" class="in s"/><label>单/包</label><input v-model="batchBagSize" type="number" min="1" class="in s"/><label>货架号</label><input v-model="batchBinCode" type="text" class="in s"/></div>
      <div class="fr"><label>步骤间隔(秒)</label><input v-model="batchStepInterval" type="number" min="0" step="0.5" class="in s"/><span class="ds" style="line-height:32px">每个大步骤开始前等待秒数</span></div>
      <div class="fr bs"><label>步骤</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('inbound')" @change="toggleBatchStep('inbound')"/>入库</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('weigh')" @change="toggleBatchStep('weigh')"/>称重</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('shelf')" @change="toggleBatchStep('shelf')"/>上架</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('unpack')" @change="toggleBatchStep('unpack')"/>拆包</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('outbound')" @change="toggleBatchStep('outbound')"/>出库通知</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('bag')" @change="toggleBatchStep('bag')"/>集包</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('vehicle')" @change="toggleBatchStep('vehicle')"/>装车</label>
        <label class="ac"><input type="checkbox" :checked="batchSteps.includes('dispatch')" @change="toggleBatchStep('dispatch')"/>发车</label>
      </div>
      <div class="fr bs" v-if="routeNodes.normal.length"><label>轨迹</label>
        <p class="ds" style="margin-bottom:4px;font-size:11px">推送顺序: 装车→干线发车→开始国内清关→国内清关完成→离开中国海关→通知清关提货→进口清关开始→清关完成→海外仓入库→海外仓出库→派送/待自提→签收成功/取件签收/客户拒签</p>
        <label class="ac" v-for="n in [...routeNodes.normal,...routeNodes.fail].sort(routeSort)" :key="n.id">
          <input type="checkbox" :checked="batchRouteIds.includes(n.id)" @change="batchRouteIds.includes(n.id)?batchRouteIds.splice(batchRouteIds.indexOf(n.id),1):batchRouteIds.push(n.id)"/> {{n.id}} {{n.name}}
        </label>
        <select v-if="routeNodes.fail.length" v-model.number="batchFailNodeId" class="in s2" style="margin-top:4px">
          <option :value="0">--派送失败(可选)--</option>
          <option v-for="n in routeNodes.fail" :key="n.id" :value="n.id">{{n.name}}</option>
        </select>
      </div>
      <button class="bt bt1" :disabled="batchLoading" @click="onBatch">{{batchLoading?'执行中...':'开始批量'}}</button>
      <div v-if="batchError" class="er">{{batchError}}</div>
      <div v-if="batchProgress.length" class="bp"><div v-for="(p,i) in batchProgress" :key="i" :class="{fl:p.startsWith('X')||p.startsWith('ERROR')}">{{p}}</div></div>
      <div v-if="batchResult?.data" class="rb"><h4>结果</h4><div class="kv" v-if="batchOrders.length"><span>运单号:</span><code v-for="(o,i) in batchOrders" :key="i" style="margin-right:4px">{{o.mail_no}}{{i<batchOrders.length-1?',':''}}</code></div><div v-if="batchResult.data.vehicle" class="kv"><span>车牌号:</span><code>{{batchResult.data.vehicle.plate}}</code></div><div class="kv"><span>大包:</span>{{batchResult.data.bags?.length||0}}个</div></div>
    </div>

    <!-- route -->
    <div v-show="activeTab==='route'" class="pnl"><h3>物流轨迹</h3><p class="ds">POST /api/TaoBaoProductPlan/TaoBaoCainiaoProductPlanAddRoute</p>
      <div class="fr"><label>路由节点</label><select v-model.number="routeNodeId" class="in"><option v-for="n in [...routeNodes.normal,...routeNodes.fail]" :key="n.id" :value="n.id">{{n.name}}</option></select></div>
      <div class="fr"><label>车辆ID</label><input v-model.number="routeVehicleId" type="number" class="in"/></div>
      <div class="fr"><label>车牌号</label><input v-model="routeBillNo" type="text" class="in"/></div>
      <button class="bt bt1" :disabled="routeLoading||!tmsToken" @click="onRoute">{{routeLoading?'推送中...':'推送轨迹'}}</button>
      <div v-if="routeError" class="er">{{routeError}}</div>
      <div v-if="routeResult" class="rb"><h4><span :class="routeResult.success?'ok':'fl'">{{routeResult.success?'成功':'失败'}}</span></h4><pre class="jd">{{JSON.stringify(routeResult.data,null,2)}}</pre></div>
    </div>
  </div>
</template>

<style scoped>
.pdd{max-width:960px;margin:0 auto;padding:24px 16px}.tb{display:flex;align-items:center;gap:16px;margin-bottom:16px}.tb h1{font-size:24px;margin:0;flex:1}.bk{padding:6px 16px;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer;font-size:14px}.cfg{display:flex;gap:24px;margin-bottom:20px;padding:8px 14px;background:#e3f2fd;border-radius:6px;font-size:12px;color:#1565c0}.gw{color:#666}
.ts{display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid #e0e0e0;flex-wrap:wrap}.tb1{padding:6px 12px;border:none;background:0 0;cursor:pointer;font-size:13px;color:#666;border-bottom:2px solid transparent;margin-bottom:-2px}.tb1:hover{color:#1976d2}.act{color:#1976d2;border-bottom-color:#1976d2;font-weight:600}
.pnl{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:24px}.pnl h3{margin:0 0 4px;font-size:18px}.ds{color:#888;font-size:13px;margin:0 0 16px}
.fr{display:flex;align-items:flex-start;gap:8px;margin-bottom:10px;flex-wrap:wrap}.fr label{min-width:50px;font-size:13px;color:#555;line-height:32px;text-align:right}
.in{flex:1;padding:6px 10px;border:1px solid #ccc;border-radius:4px;font-size:13px;font-family:inherit}.ji{font-family:Consolas,monospace;resize:vertical}.s{width:70px;min-width:70px;flex:none}.s2{width:140px;min-width:140px;flex:none}
.bt{padding:8px 20px;border:none;border-radius:4px;cursor:pointer;font-size:14px;margin-top:8px}.bt:disabled{opacity:.5;cursor:not-allowed}.bt1{background:#1976d2;color:#fff}.bt2{background:#ff9800;color:#fff}.bt3{background:#e65100;color:#fff;margin-left:8px}
.to{color:#2e7d32;font-size:13px;margin-left:8px}
.hb{margin-bottom:16px;padding:10px 14px;background:#fff8e1;border:1px solid #ffe082;border-radius:4px;font-size:12px;color:#6d4c00}.hb ul{margin:4px 0 0 16px}.hb code{background:#fff3cd;padding:1px 4px;border-radius:2px}.gv{color:#2e7d32;font-weight:700}.pp{margin-top:8px;font-size:12px;color:#e65100}.pp code{background:#fff3e0}
.ac{font-size:13px;color:#666;display:inline-flex;align-items:center;gap:4px;cursor:pointer;margin-left:8px}.ac input{margin:0}
.fb{display:flex;gap:10px;margin-top:8px;font-size:12px;flex-wrap:wrap}.fs{display:flex;align-items:center;gap:3px}.sp{display:inline-block;width:12px;height:12px;border:2px solid #ccc;border-top-color:#1976d2;border-radius:50%;animation:spin .6s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.fs.pending{color:#999}.fs.loading{color:#1976d2;font-weight:700}.fs.done{color:#2e7d32}.fs.fail{color:#c62828}
.er{margin-top:12px;padding:10px 14px;background:#ffebee;border:1px solid #ffcdd2;border-radius:4px;color:#c62828;font-size:13px}
.rb{margin-top:12px;padding:14px;background:#f5f5f5;border-radius:6px}.rb h4{margin:0 0 8px;font-size:15px}.ok{color:#2e7d32}.fl{color:#c62828}.si{margin-bottom:8px;padding:8px 10px;background:#e8f5e9;border-radius:4px}.kv{font-size:13px;margin-bottom:3px;word-break:break-all}.kv span{color:#888;margin-right:4px}.kv code{background:#e8e8e8;padding:1px 6px;border-radius:3px;font-size:12px}
.jd{background:#263238;color:#aed581;padding:12px;border-radius:4px;font-size:12px;overflow-x:auto;max-height:400px;overflow-y:auto;margin:8px 0 0}
.sb{margin-top:16px;padding:14px;background:#fafafa;border:1px solid #eee;border-radius:6px}
.ia{margin-top:16px;padding-top:16px;border-top:1px solid #e0e0e0}.dr{margin-top:12px;padding:12px;background:#fff3e0;border-radius:6px}
.bs{flex-wrap:wrap;gap:4px}.bp{margin-top:10px;font-size:12px;max-height:400px;overflow-y:auto;background:#263238;color:#aed581;padding:10px;border-radius:4px;font-family:Consolas,monospace}.bp div{margin-bottom:2px}.bp .fl{color:#ef5350}
</style>
