"""PDD 下单 + TMS 流程路由。"""

import json
from typing import Any

import httpx
import structlog
from fastapi import APIRouter

from ...tool_state import save_state, get_state
from ..common_errors import error_response
from .client import PDDOrderClient
from .config import PDDOrderConfig
from .field_generator import generate_dynamic_fields
from .models import PDDOrderRequest
from .pdd_state import save_order, update_order_status
from .product_weight import calculate_order_weight, add_or_update_product, get_product, list_products, random_pick_items

# 辅助：记录步骤状态并返回
def _step_result(tracking: str, step: str, success: bool, result: dict) -> dict:
    update_order_status(tracking, step, "done" if success else "fail",
                        "" if success else str(result.get("message", "")))
    return {"success": success, "data": result}

logger = structlog.get_logger(component="PDDOrderAPI")

router = APIRouter(prefix="/api/pdd-order", tags=["PDD下单"])

TOOL_ID = "pdd_order"


@router.get("/config")
async def get_config() -> dict[str, str]:
    config = PDDOrderConfig()
    return {
        "gateway_url": config.gateway_url,
        "app_id": config.app_id,
        "warehouse_code": config.warehouse_code,
    }


@router.get("/product-weight")
async def get_product_weight_api(item_id: str = "") -> dict:
    if not item_id:
        return {"products": list_products()}
    p = get_product(item_id)
    return {"success": bool(p), "product": p} if p else {"success": False, "message": "未找到"}


@router.post("/product-weight")
async def set_product_api(data: dict) -> dict:
    item_id = str(data.get("item_id", ""))
    if not item_id:
        return {"success": False, "message": "请提供 item_id"}
    add_or_update_product(data)
    return {"success": True, "item_id": item_id}


@router.get("/orders")
async def get_orders(batch_id: str = "") -> list[dict]:
    """查询订单列表。不传 batch_id 返回所有，传了返回该批次。"""
    import sqlite3
    from ...config import settings

    db = settings.upload_path / "tool_state.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    if batch_id:
        rows = conn.execute("SELECT * FROM pdd_orders WHERE batch_id = ? ORDER BY id", (batch_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pdd_orders ORDER BY id DESC LIMIT 50").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


@router.post("/create")
async def pdd_create_order(request: PDDOrderRequest) -> dict[str, Any]:
    """创建 PDD 集运订单。

    后端自动生成 5 个动态字段并计算 MD5 签名后发送。
    """
    print("[PDD ROUTER] create enter")
    order_json_str = json.dumps(request.order_body, ensure_ascii=False)
    save_key = "home_json" if request.delivery_type == "homeDelivery" else "pickup_json"
    save_state(TOOL_ID, {
        "delivery_type": request.delivery_type,
        save_key: order_json_str,
    })

    try:
        body = {**request.order_body, "deliveryType": request.delivery_type}
        resolved = generate_dynamic_fields(body)

        async with PDDOrderClient() as client:
            result = await client.create_order(resolved)

        if result.get("success"):
            save_order(
                delivery_type=request.delivery_type,
                logistics_order_code=resolved.get("logisticsOrderCode", ""),
                mail_no=(resolved.get("mailDetails") or [{}])[0].get("mailNo", ""),
                pp_code=resolved["logisticsOrderCode"].replace("PC", "PP", 1) if "logisticsOrderCode" in resolved else "",
                order_code=resolved["logisticsOrderCode"].replace("PC", "PP", 1) if request.delivery_type == "homeDelivery" else resolved.get("logisticsOrderCode", ""),
                buyer_code=resolved.get("buyerCode", ""),
                trade_sn=(resolved.get("paymentDetail") or {}).get("tradeOrderSn", ""),
            )

        return {
            "success": result.get("success", False),
            "data": result,
            "sent_logistics_order_code": resolved.get("logisticsOrderCode", ""),
            "sent_buyer_code": resolved.get("buyerCode", ""),
            "sent_dere_recog_code": resolved.get("dereRecogCode", ""),
            "sent_trade_order_sn": (resolved.get("paymentDetail") or {}).get("tradeOrderSn", ""),
            "sent_mail_no": (resolved.get("mailDetails") or [{}])[0].get("mailNo", ""),
        }
    except httpx.TimeoutException as e:
        logger.error("pdd_create_order_timeout", error=str(e), delivery_type=request.delivery_type)
        return {"success": False, "error_code": "TIMEOUT_ERROR", "message": f"请求PDD网关超时: {e}"}
    except httpx.HTTPError as e:
        logger.error("pdd_create_order_http_error", error=str(e), error_type=type(e).__name__, delivery_type=request.delivery_type)
        return {"success": False, "error_code": "NETWORK_ERROR", "message": f"网络错误: {type(e).__name__}: {e}"}
    except Exception as e:
        logger.error("pdd_create_order_error", error=str(e), error_type=type(e).__name__)
        return {"success": False, "error_code": "UNKNOWN_ERROR", "message": f"下单异常: {type(e).__name__}: {e}"}


# ================================================================
# TMS 流程
# ================================================================

@router.post("/tms-login")
async def pdd_tms_login(data: dict[str, Any]) -> dict[str, Any]:
    """TMS 登录，返回 JWT token。"""
    config = PDDOrderConfig()
    job_number = str(data.get("job_number", "")).strip()
    password = str(data.get("password", "")).strip()
    tms_user = job_number or config.tms_user
    tms_pass = password or config.tms_password

    if not tms_user or not tms_pass:
        return {"success": False, "message": "请配置 TMS 用户名和密码"}

    save_state(TOOL_ID, {"tms_job_number": tms_user, "tms_password": tms_pass})

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/Login/NewLogin",
                json={"jobNumber": tms_user, "password": tms_pass},
                headers={"Content-Type": "application/json"},
            )
            data_rsp = rsp.json()
            if data_rsp.get("state") and data_rsp.get("data"):
                token = data_rsp["data"]
                save_state(TOOL_ID, {"tms_token": token})
                return {"success": True, "token": token}
            return {"success": False, "message": f"登录失败: {data_rsp}"}
    except Exception as e:
        return error_response(e)


@router.post("/inbound")
async def pdd_inbound(data: dict[str, Any]) -> dict[str, Any]:
    """揽收入库。

    入参: token (TMS JWT), tracking_number (mailNo)
    """
    token = str(data.get("token", "")).strip()
    tracking_number = str(data.get("tracking_number", "")).strip()
    config = PDDOrderConfig()

    if not token:
        return {"success": False, "message": "请先登录 TMS"}
    if not tracking_number:
        return {"success": False, "message": "请输入运单号"}

    save_state(TOOL_ID, {"inbound_tracking_number": tracking_number})

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/Warehouse/CustomerOrderInStorage",
                json={"trackingNumber": tracking_number},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )
            result = rsp.json()
            return _step_result(tracking_number, "inbound",
                result.get("state", False) or result.get("code") == 200, result)
    except Exception as e:
        return error_response(e)


@router.post("/shelf")
async def pdd_shelf(data: dict[str, Any]) -> dict[str, Any]:
    """上架。"""
    token = str(data.get("token", "")).strip()
    tracking_number = str(data.get("tracking_number", "")).strip()
    warehouse_code = str(data.get("warehouse_code", "langfang_warehouse_1")).strip()
    bin_code = str(data.get("bin_code", "A1-1-2")).strip()
    config = PDDOrderConfig()
    if not token:
        return {"success": False, "message": "请先登录 TMS"}
    save_state(TOOL_ID, {"shelf_tracking_number": tracking_number,
                          "shelf_warehouse_code": warehouse_code,
                          "shelf_bin_code": bin_code})
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/Warehouse/PutPackageOrderOnShelf",
                json={"trackNumber": tracking_number,
                      "putOnWarehouseCode": warehouse_code,
                      "binCode": bin_code},
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            )
            result = rsp.json()
            return _step_result(tracking_number, "shelf",
                result.get("state", False) or result.get("code") == 200, result)
    except Exception as e:
        return error_response(e)


@router.post("/auto-weigh")
async def pdd_auto_weigh(data: dict[str, Any]) -> dict[str, Any]:
    """自动称重 (SyncCrossLineData)，不需要 token。"""
    save_state(TOOL_ID, {
        "weigh_trackcode": str(data.get("trackcode", "")),
        "weigh_length": str(data.get("length", "")),
        "weigh_width": str(data.get("width", "")),
        "weigh_height": str(data.get("height", "")),
        "weigh_weight": str(data.get("weight", "")),
    })
    config = PDDOrderConfig()
    body = {k: v for k, v in data.items() if k != "token"}
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/Equipment/SyncCrossLineData",
                json=body,
                headers={"Content-Type": "application/json"},
            )
            result = rsp.json()
            return _step_result(str(data.get("trackcode","")), "weigh",
                "成功" in str(result.get("result_msg", "")), result)
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/manual-weigh")
async def pdd_manual_weigh(data: dict[str, Any]) -> dict[str, Any]:
    """手动称重 (CaiNiaoKzOrderManualWeight)。"""
    save_state(TOOL_ID, {
        "weigh_order_number": str(data.get("order_number", "")),
        "weigh_tracking_number": str(data.get("tracking_number", "")),
        "weigh_length": str(data.get("length", "")),
        "weigh_width": str(data.get("width", "")),
        "weigh_height": str(data.get("height", "")),
        "weigh_weight": str(data.get("weight", "")),
    })
    items = data.get("items", [])
    weight_val = data.get("weight", 1.25)
    if items:
        weight_val = calculate_order_weight(items)

    body = {
        "orderNumber": str(data.get("order_number", "")),
        "trackingNumber": str(data.get("tracking_number", "")),
        "length": data.get("length"),
        "width": data.get("width"),
        "height": data.get("height"),
        "weight": weight_val,
    }
    return await _tms_post_raw(data.get("token", ""), "/api/CustomerOrderCaiNiaoKz/CaiNiaoKzOrderManualWeight", body)


async def _tms_post(
    data: dict[str, Any],
    path: str,
) -> dict[str, Any]:
    """通用 TMS POST 调用（直接透传 data 除 token 外的字段）。"""
    token = str(data.get("token", "")).strip()
    body = {k: v for k, v in data.items() if k != "token"}
    return await _tms_post_raw(token, path, body)


async def _tms_post_raw(
    token: Any,
    path: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """通用 TMS POST 调用（指定 body）。"""
    token = str(token or "").strip()
    config = PDDOrderConfig()
    if not token:
        return {"success": False, "message": "请先登录 TMS"}

    try:
        url = f"{config.tms_host}{path}"
        print(f"[TMS] POST {url}")
        print(f"[TMS] BODY {body}")
        print(f"[TMS] TOKEN {token[:30]}...")
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}{path}",
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )
            result = rsp.json()
            print(f"[TMS] RESP {rsp.status_code} {str(result)[:300]}")
            success = result.get("state", False) or result.get("code") == 200
            return {"success": success, "data": result}
    except Exception as e:
        return error_response(e)


@router.post("/unpack")
async def pdd_unpack(data: dict[str, Any]) -> dict[str, Any]:
    """拆包通知 (PDD)。"""
    logistics_order_code = str(data.get("logistics_order_code", "")).strip()
    buyer_code = str(data.get("buyer_code", "")).strip()
    mail_no = str(data.get("mail_no", "")).strip()
    delivery_type = str(data.get("delivery_type", "homeDelivery")).strip()
    receiver = data.get("receiver_detail", {})

    if not logistics_order_code:
        return {"success": False, "message": "缺少 logistics_order_code"}

    pp_code = logistics_order_code.replace("PC", "PP", 1)
    order_code = pp_code if delivery_type == "homeDelivery" else logistics_order_code
    body = {
        "orderCode": order_code,
        "buyerCode": buyer_code,
        "providerCode": "KIMIGO_MN",
        "consoWarehouseCode": "KIMIGO",
        "consoType": "DIRECT_MAIL_DIRECT_ROAD",
        "deliveryType": delivery_type,
        "mailDetails": [{"expressCode": "SF", "mailNo": mail_no}],
        "receiverDetail": receiver,
    }

    save_state(TOOL_ID, {"unpack_logistics_order_code": logistics_order_code})

    return await _pdd_post(body, "/api/pdd/callback/conso/unpack/notice", order_code, "unpack", logistics_order_code)


@router.post("/outbound")
async def pdd_outbound(data: dict[str, Any]) -> dict[str, Any]:
    """出库通知 (PDD)。"""
    logistics_order_code = str(data.get("logistics_order_code", "")).strip()
    buyer_code = str(data.get("buyer_code", "")).strip()
    mail_no = str(data.get("mail_no", "")).strip()
    trade_order_sn = str(data.get("trade_order_sn", "")).strip()
    delivery_type = str(data.get("delivery_type", "homeDelivery")).strip()
    receiver = data.get("receiver_detail", {})
    order_items = data.get("order_items", [])
    weight = data.get("weight", 1250)

    if not logistics_order_code:
        return {"success": False, "message": "缺少 logistics_order_code"}

    pp_code = logistics_order_code.replace("PC", "PP", 1)
    order_code = pp_code if delivery_type == "homeDelivery" else logistics_order_code
    body = {
        "orderCode": order_code,
        "buyerCode": buyer_code,
        "providerCode": "KIMIGO_MN",
        "consoWarehouseCode": "KIMIGO",
        "consoType": "DIRECT_MAIL_DIRECT_ROAD",
        "deliveryType": delivery_type,
        "outboundType": "CONSO",
        "logisticsOrderCodes": [logistics_order_code],
        "orderSns": [trade_order_sn],
        "mailDetails": [{
            "expressCode": "SF",
            "mailNo": mail_no,
            "weight": weight,
            "consoWarehouseCode": "KIMIGO",
        }],
        "receiverDetail": receiver,
        "orderDetails": [{
            "orderSn": trade_order_sn,
            "logisticsOrderCode": logistics_order_code,
            "items": order_items,
        }],
        "stationCode": "UB-A-0002",
    }

    save_state(TOOL_ID, {"outbound_logistics_order_code": logistics_order_code})

    return await _pdd_post(body, "/api/pdd/callback/conso/outbound/notice", order_code, "outbound", logistics_order_code)


@router.post("/bag")
async def pdd_bag(data: dict[str, Any]) -> dict[str, Any]:
    """集包：查合单号 → 建空大包 → 查包号 → 扫码集包（支持多条）。"""
    token = str(data.get("token", "")).strip()
    pp_code = str(data.get("pp_code", "")).strip()
    mail_nos_str = str(data.get("mail_nos", "")).strip()
    outbound_type = data.get("outbound_type", 1)
    config = PDDOrderConfig()
    if not token:
        return {"success": False, "message": "请先登录 TMS"}

    mail_nos = [m.strip() for m in mail_nos_str.split(",") if m.strip()]
    if not mail_nos:
        return {"success": False, "message": "请提供运单号"}

    save_state(TOOL_ID, {"bag_pp_code": pp_code, "bag_mail_nos": mail_nos_str})

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        import pymysql
        conn = pymysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, database=config.db_name, charset="utf8mb4",
        )
        cur = conn.cursor()

        # 1. 查合单号/尾程单号（上门查JY，自提查UHMS）
        combined_nos = []
        if outbound_type == 1:
            for mn in mail_nos:
                cur.execute(
                    "SELECT cpc.last_mile_order_number FROM customer_package_combined_order_nz cpc "
                    "JOIN customer_package_order_tracking cpot ON cpc.id=cpot.customer_package_combined_order_id "
                    "WHERE cpot.tracking_number=%s ORDER BY cpc.id DESC LIMIT 1", (mn,)
                )
                row = cur.fetchone()
                if row:
                    combined_nos.append(row[0])
        else:
            for mn in mail_nos:
                cur.execute(
                    "SELECT ky_in_storage_number FROM customer_order WHERE tracking_number=%s ORDER BY id DESC LIMIT 1", (mn,)
                )
                row = cur.fetchone()
                if row and row[0]:
                    combined_nos.append(row[0])
        if not combined_nos:
            cur.close(); conn.close()
            return {"success": False, "message": "未找到合单号，请先执行拆包+出库（上门）或确认运单号（自提）"}

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # 2. 建空大包
            rsp = await client.post(
                f"{config.tms_host}/api/CustomerOutbound/AddPddEmptyCustomerOutBound",
                json={        "outboundType": outbound_type, "countryCode": "MN", "customerCode": "Pdd-Mn",
                      "printCount": 1, "outboundMode": 1},
                headers=headers,
            )
            bag_data = rsp.json()

            # 3. 查包号
            cur.execute("SELECT id, outbound_number FROM customer_outbound ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            cur.close(); conn.close()
            if not row:
                return {"success": False, "message": "未查到包号", "data": bag_data}
            bag_id, bag_no = row[0], row[1]

            # 4. 扫码集包（可扫多个合单号）
            scan_results = []
            for cno in combined_nos:
                rsp2 = await client.post(
                    f"{config.tms_host}/api/CustomerOutbound/PackageInStorge",
                    json={"id": bag_id, "kySmallShipment": cno, "outboundSource": 0},
                    headers=headers,
                )
                scan_results.append(rsp2.json())
            return {"success": True, "data": {"bag_id": bag_id, "bag_no": bag_no,
                    "combined_nos": combined_nos, "create_bag": bag_data, "scan": scan_results}}
    except Exception as e:
        return error_response(e)


@router.post("/vehicle")
async def pdd_vehicle(data: dict[str, Any]) -> dict[str, Any]:
    """装车：建车 → 查车辆ID → 包挂车。"""
    token = str(data.get("token", "")).strip()
    bag_nos = data.get("bag_nos", [])
    if isinstance(bag_nos, str):
        bag_nos = [n.strip() for n in bag_nos.split(",") if n.strip()]
    if not bag_nos:
        return {"success": False, "message": "请提供包号"}
    config = PDDOrderConfig()
    if not token:
        return {"success": False, "message": "请先登录 TMS"}

    import time as _time
    from datetime import datetime
    plate = f"MN{datetime.now().strftime('%y%m%d')}{int(_time.time() * 1000)}"
    save_state(TOOL_ID, {"vehicle_plate": plate, "vehicle_bag_nos": ",".join(bag_nos)})
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # 1. 建车
            rsp = await client.post(
                f"{config.tms_host}/api/ProductPlanBillBasic/AddAndUpdateProductPlanBillBasicV2",
                json={"countryCode": "MN", "billLadingNo": plate, "remark": ""},
                headers=headers,
            )
            vehicle_data = rsp.json()

            # 2. 查车辆 ID（只读，不加锁）
            import pymysql
            conn = pymysql.connect(
                host=config.db_host, port=config.db_port, user=config.db_user,
                password=config.db_password, database=config.db_name, charset="utf8mb4",
            )
            cur = conn.cursor()
            cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
            cur.execute(
                "SELECT id FROM product_plan_bill_basic WHERE bill_lading_no=%s AND country_code='MN'",
                (plate,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return {"success": False, "message": "未查到车辆ID", "data": vehicle_data}
            vehicle_id = row[0]

            # 3. 包挂车
            rsp2 = await client.post(
                f"{config.tms_host}/api/ProductPlanBillBasic/AddProductPlanBillBasicSend",
                json={"productPlanBillBasicId": vehicle_id,
                      "sortingAreaPackagingNumberList": bag_nos,
                      "customerCode": "Pdd-Mn"},
                headers=headers,
            )
            send_data = rsp2.json()
            return {"success": True, "data": {"plate": plate, "vehicle_id": vehicle_id,
                    "create_vehicle": vehicle_data, "attach_bags": send_data}}
    except Exception as e:
        return error_response(e)


@router.post("/dispatch")
async def pdd_dispatch(data: dict[str, Any]) -> dict[str, Any]:
    """发车。"""
    token = str(data.get("token", "")).strip()
    vehicle_id = data.get("vehicle_id")
    customer_id = str(data.get("customer_id", "13")).strip()
    config = PDDOrderConfig()
    if not token:
        return {"success": False, "message": "请先登录 TMS"}
    if not vehicle_id:
        return {"success": False, "message": "请提供车辆ID"}

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.get(
                f"{config.tms_host}/api/ProductPlanBillBasic/UpdateProductPlanBillBasicSetOffCar",
                params={"id": vehicle_id, "customerId": customer_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            result = rsp.json()
            return {"success": result.get("state", False) or result.get("code") == 200, "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}


ROUTE_NODES = {
    165:"干线发车",166:"开始国内清关",167:"国内清关完成",168:"离开中国海关",
    169:"通知清关提货",170:"进口清关开始",171:"清关完成",172:"海外仓已出库",
    173:"取件签收",174:"待自提",175:"客户拒签",176:"海外仓入库",177:"进口清关查验",
    178:"进口清关失败",179:"出口清关失败",180:"出口清关查验",197:"中国仓转运",
    209:"签收成功",210:"海关查验",
    211:"派送失败(异常天气)",212:"派送失败(客户电话无人接听)",
    213:"派送失败(客户要求改派地址)",214:"派送失败(与客户协商另约时间派送)",215:"派送失败(客户电话错误)",
    216:"派送失败(客户地址锴误)",217:"派送失败(其他原因失败)",218:"派送失败(客户地址不详且联系不到客户)",
    219:"派送",220:"派送失败（客户拒签）",224:"装车",
}

# 派送失败节点（互斥，只选一个）
ROUTE_FAIL_NODES = {k:v for k,v in ROUTE_NODES.items() if "派送失败" in v}
# 普通节点（可多选）
ROUTE_NORMAL_NODES = {k:v for k,v in ROUTE_NODES.items() if "派送失败" not in v}

# 推送顺序（越小越先推）
ROUTE_ORDER = {
    224:1,  # 装车
    165:2,  # 干线发车
    166:3,  # 开始国内清关
    167:4,  # 国内清关完成
    168:5,  # 离开中国海关
    169:6,  # 通知清关提货
    170:7,  # 进口清关开始
    171:8,  # 清关完成
    176:9,  # 海外仓入库
    172:10, # 海外仓出库
    219:11, # 派送
    174:11, # 待自提
    209:12, # 签收成功
    173:12, # 取件签收
    175:12, # 客户拒签
}

# 步骤中文名 -> 英文 key（批量流程用）
STEP_KEY_MAP = {
    "下单": "order",
    "入库": "inbound",
    "称重": "weigh",
    "上架": "shelf",
    "拆包": "unpack",
    "出库通知": "outbound",
    "集包": "bag",
    "装车": "vehicle",
    "发车": "dispatch",
}


@router.get("/route-nodes")
async def get_route_nodes() -> dict:
    """获取路由节点列表（分组）。"""
    return {
        "normal": [{"id":k,"name":v} for k,v in ROUTE_NORMAL_NODES.items()],
        "fail": [{"id":k,"name":v} for k,v in ROUTE_FAIL_NODES.items()],
    }


@router.post("/route")
async def pdd_route(data: dict[str, Any]) -> dict[str, Any]:
    """推送物流轨迹。"""
    token = str(data.get("token", "")).strip()
    vehicle_id = data.get("vehicle_id") or data.get("product_plan_bill_basic_id")
    node_id = data.get("customer_route_node_id")
    bill_no = str(data.get("bill_lading_no", "")).strip()
    config = PDDOrderConfig()

    if not token:
        return {"success": False, "message": "请先登录 TMS"}
    if not vehicle_id or not node_id:
        return {"success": False, "message": "请提供车辆ID和路由节点"}

    body = {
        "id": vehicle_id,
        "customerId": 13,
        "customerRouteNodeId": node_id,
        "isRemark": 0,
        "remark": "",
        "remarkEnglishName": "",
        "remarkRussiaName": "",
        "remarkKazakhstanName": "",
        "customerRoutingNodeChineseName": ROUTE_NODES.get(node_id, ""),
        "billLadingNo": bill_no,
        "productPlanBillBasicId": vehicle_id,
    }
    save_state(TOOL_ID, {"route_vehicle_id": vehicle_id, "route_bill_no": bill_no})

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/TaoBaoProductPlan/TaoBaoCainiaoProductPlanAddRoute",
                json=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            )
            result = rsp.json()
            return {"success": result.get("state", False) or result.get("code") == 200, "data": result}
    except Exception as e:
        return error_response(e)


async def _ensure_tms_token(token: str | None = None) -> tuple[bool, str, str]:
    """确保有有效的 TMS token。

    如果传入 token 有效则直接返回；否则尝试用保存的账号密码自动登录。
    返回 (success, token, message)。
    """
    if token and token.strip():
        return True, token.strip(), ""

    state = get_state(TOOL_ID)
    saved_token = state.get("tms_token", "")
    if saved_token:
        return True, saved_token, ""

    tms_user = state.get("tms_job_number", "")
    tms_pass = state.get("tms_password", "")
    if not tms_user or not tms_pass:
        config = PDDOrderConfig()
        tms_user = tms_user or config.tms_user
        tms_pass = tms_pass or config.tms_password

    if not tms_user or not tms_pass:
        return False, "", "请先在揽收入库Tab登录TMS（未配置自动登录账号）"

    try:
        async with httpx.AsyncClient(timeout=PDDOrderConfig().timeout) as client:
            rsp = await client.post(
                f"{PDDOrderConfig().tms_host}/api/Login/NewLogin",
                json={"jobNumber": tms_user, "password": tms_pass},
                headers={"Content-Type": "application/json"},
            )
            data_rsp = rsp.json()
            if data_rsp.get("state") and data_rsp.get("data"):
                new_token = data_rsp["data"]
                save_state(TOOL_ID, {"tms_token": new_token})
                return True, new_token, ""
            return False, "", f"自动登录TMS失败: {data_rsp}"
    except Exception as e:
        return False, "", f"自动登录TMS异常: {e}"


@router.post("/batch")
async def pdd_batch(data: dict[str, Any]):
    """批量创建订单并推送全流程（SSE 流式返回进度）。-"""
    import asyncio, time as _time, json as _json
    from fastapi.responses import StreamingResponse

    home_count = int(data.get("home_count", 0))
    pickup_count = int(data.get("pickup_count", 0))
    order_count = home_count + pickup_count
    bag_group_size = int(data.get("bag_group_size", 1))
    steps = data.get("steps", [])
    token_input = str(data.get("token", "")).strip()
    order_body = data.get("order_body", {})
    state = get_state(TOOL_ID)
    try:
        home_body = json.loads(state.get("home_json", "")) if state.get("home_json") else None
    except Exception:
        home_body = None
    try:
        pickup_body = json.loads(state.get("pickup_json", "")) if state.get("pickup_json") else None
    except Exception:
        pickup_body = None
    if not home_body:
        home_body = order_body or {}
    if not pickup_body:
        pickup_body = order_body or {}
    delivery_type = str(data.get("delivery_type", "homeDelivery")).strip()
    warehouse_code = str(data.get("warehouse_code", "langfang_warehouse_1")).strip()
    bin_code = str(data.get("bin_code", "A1-1-2")).strip()
    route_ids = data.get("route_ids", [])
    step_interval = float(data.get("step_interval", 0) or 0)
    if isinstance(route_ids, list):
        route_ids = sorted(route_ids, key=lambda r: ROUTE_ORDER.get(r, 999))
    config = PDDOrderConfig()
    save_state(TOOL_ID, {"batch_home_count": str(home_count), "batch_pickup_count": str(pickup_count),
                          "batch_bag_size": str(bag_group_size), "batch_bin_code": bin_code,
                          "batch_step_interval": str(step_interval)})

    if order_count < 1:
        return {"success": False, "message": "至少需要1个订单"}

    login_ok, tms_token, login_msg = await _ensure_tms_token(token_input)
    if not login_ok:
        return {"success": False, "message": login_msg}

    # 生成订单队列：[{type:'home', dt:'homeDelivery'}, ...]
    order_queue = [{"type":"home","dt":"homeDelivery"}] * home_count + [{"type":"pickup","dt":"selfPickup"}] * pickup_count

    async def event_stream():
        from datetime import datetime
        import pymysql
        conn = pymysql.connect(host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, database=config.db_name, charset="utf8mb4")
        cur = conn.cursor()
        orders = []
        success_orders = []

        async def sse(event: str, d: dict):
            yield f"event: {event}\ndata: {_json.dumps(d, ensure_ascii=False)}\n\n"

        async def tms_post(p: str, b: dict) -> dict:
            async with httpx.AsyncClient(timeout=config.timeout) as c:
                r = await c.post(f"{config.tms_host}{p}", json=b,
                    headers={"Content-Type":"application/json","Authorization":f"Bearer {tms_token}"})
                return r.json()

        try:
            # 阶段1：批量下单
            async for m in sse("step", {"step":"下单","status":"loading","msg":f"创建{order_count}个订单..."}): yield m
            for i, oq in enumerate(order_queue):
                dt = oq["dt"]
                template = home_body if oq["type"] == "home" else pickup_body
                body = {**template, "deliveryType": dt}
                try:
                    async for m in sse("progress", {"msg": f"开始下单 {i+1}/{order_count} [{oq['type']}]..."}): yield m
                    resolved = generate_dynamic_fields(body)
                    async with PDDOrderClient() as client:
                        result = await client.create_order(resolved)
                    ok = result.get("success", False)
                except Exception as ex:
                    resolved = generate_dynamic_fields(body)
                    ok = False
                    result = {"success": False, "message": str(ex)}
                    err_detail = f"{type(ex).__name__}: {ex} args={getattr(ex, 'args', [])}"
                    async for m in sse("progress", {"msg": f"下单 {i+1}/{order_count} 异常: {err_detail}"}): yield m
                mail_no = (resolved.get("mailDetails") or [{}])[0].get("mailNo", "")
                pc_code = resolved.get("logisticsOrderCode", "")
                pp_code = pc_code.replace("PC", "PP", 1)
                order_code = pp_code if delivery_type == "homeDelivery" else pc_code
                buyer_code = resolved.get("buyerCode", "")
                trade_sn = (resolved.get("paymentDetail") or {}).get("tradeOrderSn", "")
                o = {"index": i+1, "success": ok, "mail_no": mail_no, "pc_code": pc_code,
                     "pp_code": pp_code, "order_code": order_code, "buyer_code": buyer_code, "trade_sn": trade_sn,
                     "delivery_type": dt, "items": template.get("items",[]),
                     "buyer_detail": template.get("buyerDetail",{})}
                orders.append(o)
                if ok: success_orders.append(o)
                async for m in sse("progress", {"idx": i+1, "total": order_count, "mail_no": mail_no, "ok": ok, "type": oq["type"]}): yield m
                if ok:
                    await asyncio.sleep(0.3)
            async for m in sse("step", {"step":"下单","status":"done","msg":f"完成 {len(success_orders)}/{order_count}"}): yield m

            # 辅助
            async def run_step(name, fn, *, must_succeed: bool = False):
                key = STEP_KEY_MAP.get(name, name)
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[{name}] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":name,"key":key,"status":"loading","msg":"执行中..."}): yield m
                ok=0; errs=[]
                for o in success_orders:
                    rez,body=await fn(o)
                    if rez: ok+=1
                    else: errs.append({"mail_no":o["mail_no"],"body":body})
                st="done" if ok == len(success_orders) else "fail"
                async for m in sse("step",{"step":name,"key":key,"status":st,"msg":f"{ok}/{len(success_orders)}","errors":errs if errs else None}): yield m
                if must_succeed and ok != len(success_orders):
                    async for m in sse("error",{"message":f"{name}未全部成功，终止批量流程","errors":errs}): yield m
                    yield {"__stop__": True}

            async def inbound_fn(o):
                b={"trackingNumber":o["mail_no"]}
                r=await tms_post("/api/Warehouse/CustomerOrderInStorage",b)
                ok=r.get("state") or r.get("code")==200; o["inbound"]=ok; return ok,b
            async def weigh_fn(o):
                wt = calculate_order_weight(o.get("items", []))
                b={"trackcode":o["mail_no"],"length":20.5,"width":15,"height":10,"weight":wt}
                r=await tms_post("/api/Equipment/SyncCrossLineData",b)
                ok=bool(r.get("state") or r.get("code")==200 or "成功" in str(r.get("result_msg","")))
                o["weigh"]=ok
                return ok,b
            async def shelf_fn(o):
                b={"trackNumber":o["mail_no"],"putOnWarehouseCode":warehouse_code,"binCode":bin_code}
                r=await tms_post("/api/Warehouse/PutPackageOrderOnShelf",b)
                ok=r.get("state") or r.get("code")==200; o["shelf"]=ok; return ok,b

            if "inbound" in steps:
                async for m in run_step("入库",inbound_fn, must_succeed=True):
                    if isinstance(m, dict) and m.get("__stop__"):
                        return
                    yield m
            if "weigh" in steps:
                async for m in run_step("称重",weigh_fn, must_succeed=True):
                    if isinstance(m, dict) and m.get("__stop__"):
                        return
                    yield m
            if "shelf" in steps:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[上架] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"上架","key":"shelf","status":"loading","msg":"执行中..."}): yield m
                home = [o for o in success_orders if o.get("delivery_type")=="homeDelivery"]
                ok=0; errs=[]
                for o in home:
                    b={"trackNumber":o["mail_no"],"putOnWarehouseCode":warehouse_code,"binCode":bin_code}
                    r=await tms_post("/api/Warehouse/PutPackageOrderOnShelf",b)
                    rez=r.get("state") or r.get("code")==200; o["shelf"]=rez
                    if rez: ok+=1
                    else: errs.append({"mail_no":o["mail_no"],"body":b})
                st="done" if ok == len(home) else "fail"
                async for m in sse("step",{"step":"上架","key":"shelf","status":st,"msg":f"{ok}/{len(home)}跳过{len(success_orders)-len(home)}自提","errors":errs if errs else None}): yield m
                if not ok and home:
                    async for m in sse("error",{"message":"上架未全部成功，终止批量流程","errors":errs}): yield m
                    return

            if "unpack" in steps:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[拆包] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                home = [o for o in success_orders if o.get("delivery_type")=="homeDelivery"]
                async for m in sse("step",{"step":"拆包","key":"unpack","status":"loading","msg":"执行中..."}): yield m
                ok=0; errs=[]
                for o in home:
                    ub={"orderCode":o["order_code"],"buyerCode":o["buyer_code"],"providerCode":"KIMIGO_MN","consoWarehouseCode":"KIMIGO","consoType":"DIRECT_MAIL_DIRECT_ROAD","deliveryType":o.get("delivery_type","homeDelivery"),"mailDetails":[{"expressCode":"SF","mailNo":o["mail_no"]}],"receiverDetail":order_body.get("buyerDetail",{})}
                    r2=await _pdd_post_raw(ub,"/api/pdd/callback/conso/unpack/notice")
                    o["unpack"]=r2.get("success")
                    if o["unpack"]: ok+=1
                    else: errs.append({"mail_no":o["mail_no"],"body":ub})
                st="done" if (ok == len(home)) else "fail"
                async for m in sse("step",{"step":"拆包","key":"unpack","status":st,"msg":f"{ok}/{len(home)}跳过{len(success_orders)-len(home)}自提","errors":errs if errs else None}): yield m
                if not ok and home:
                    async for m in sse("error",{"message":"拆包全部失败","errors":errs}): yield m
                    return
                await asyncio.sleep(2)

            if "outbound" in steps:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[出库通知] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"出库通知","key":"outbound","status":"loading","msg":"执行中..."}): yield m
                ok=0; errs=[]
                for o in success_orders:
                    dt = o.get("delivery_type", delivery_type)
                    items = o.get("items", order_body.get("items", []))
                    receiver = o.get("buyer_detail", order_body.get("buyerDetail", {}))
                    ec = o["mail_no"][:2] if len(o["mail_no"]) >= 2 else "SF"
                    outbound_weight = int(calculate_order_weight(items) * 1000)
                    ob={"orderCode":o["order_code"],"buyerCode":o["buyer_code"],"providerCode":"KIMIGO_MN","consoWarehouseCode":"KIMIGO","consoType":"DIRECT_MAIL_DIRECT_ROAD","deliveryType":dt,"outboundType":"CONSO","logisticsOrderCodes":[o["pc_code"]],"orderSns":[o.get("trade_sn","")],"mailDetails":[{"expressCode":ec,"mailNo":o["mail_no"],"weight":outbound_weight,"consoWarehouseCode":"KIMIGO"}],"receiverDetail":receiver,"orderDetails":[{"orderSn":o.get("trade_sn",""),"logisticsOrderCode":o["pc_code"],"items":items}],"stationCode":"UB-A-0002"}
                    print(f"[BATCH OUTBOUND] mail_no={o['mail_no']} weight={outbound_weight} body={ob}")
                    r2=await _pdd_post_raw(ob,"/api/pdd/callback/conso/outbound/notice")
                    print(f"[BATCH OUTBOUND] mail_no={o['mail_no']} response={r2}")
                    o["outbound"]=r2.get("success")
                    if o["outbound"]: ok+=1
                    else: errs.append({"mail_no":o["mail_no"],"body":ob, "response": r2})
                st="done" if ok else "fail"
                async for m in sse("step",{"step":"出库通知","key":"outbound","status":st,"msg":f"{ok}/{len(success_orders)}","errors":errs if errs else None}): yield m
                if not ok:
                    async for m in sse("error",{"message":"出库全部失败","errors":errs}): yield m
                    return
                await asyncio.sleep(2)

            # 集包
            bags=[]
            if "bag" in steps:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[集包] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"集包","key":"bag","status":"loading","msg":"执行中..."}): yield m
                # 按配送类型分组
                home_orders = [o for o in success_orders if o.get("delivery_type") == "homeDelivery"]
                pickup_orders = [o for o in success_orders if o.get("delivery_type") != "homeDelivery"]
                all_groups = []
                for olist,ob_type in [(home_orders,1),(pickup_orders,0)]:
                    if not olist: continue
                    groups=[olist[i:i+bag_group_size] for i in range(0,len(olist),bag_group_size)]
                    all_groups.append((groups,ob_type))
                # 先全部上门包，再全部自提包
                gi = 0
                total_groups = sum(len(grps) for grps, _ in all_groups)
                for grps, ob_type in all_groups:
                    for group in grps:
                        gi += 1
                        combined_nos=[]
                        for o in group:
                            if ob_type == 1:
                                cur.execute("SELECT cpc.last_mile_order_number FROM customer_package_combined_order_nz cpc JOIN customer_package_order_tracking cpot ON cpc.id=cpot.customer_package_combined_order_id WHERE cpot.tracking_number=%s ORDER BY cpc.id DESC LIMIT 1",(o["mail_no"],))
                            else:
                                cur.execute("SELECT ky_in_storage_number FROM customer_order WHERE tracking_number=%s ORDER BY id DESC LIMIT 1",(o["mail_no"],))
                            row=cur.fetchone()
                            if row and row[0]: combined_nos.append(row[0])
                        if not combined_nos:
                            async for m in sse("progress",{"msg":f"跳过空包: {[o['mail_no'] for o in group]} (无合单号/尾程号)"}): yield m
                            continue
                        r=await tms_post("/api/CustomerOutbound/AddPddEmptyCustomerOutBound",{"outboundType":ob_type,"countryCode":"MN","customerCode":"Pdd-Mn","printCount":1,"outboundMode":1})
                        if not (r.get("state") or r.get("code") == 200):
                            async for m in sse("progress",{"msg":f"创建大包失败: {r}"}): yield m
                            continue
                        # 用创建前时间点过滤，避免查到旧包
                        from datetime import timedelta
                        create_before = (datetime.now() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                        await asyncio.sleep(1)
                        cur.execute(
                            "SELECT id,outbound_number FROM customer_outbound WHERE create_time > %s AND outbound_mode=1 ORDER BY id DESC LIMIT 1",
                            (create_before,)
                        )
                        row=cur.fetchone()
                        if not row:
                            async for m in sse("progress",{"msg":f"未查到新创建的大包 (after {create_before})"}): yield m
                            continue
                        bag_id,bag_no=row[0],row[1]
                        for cno in combined_nos:
                            print(f"[BATCH BAG] {cno} 关联大包 {bag_no}(id={bag_id})")
                            await tms_post("/api/CustomerOutbound/PackageInStorge",{"id":bag_id,"kySmallShipment":cno,"outboundSource":0})
                        bags.append({"bag_no":bag_no,"count":len(group),"orders":[o["index"] for o in group],"combined_nos":combined_nos,"type":"上门" if ob_type==1 else "自提"})
                        print(f"[BATCH BAG] 包{bag_no} type={ob_type} orders={[o['mail_no'] for o in group]} combined={combined_nos}")
                        async for m in sse("progress",{"idx":gi,"total":total_groups,"bag_no":bag_no,"count":len(group)}): yield m
                async for m in sse("step",{"step":"集包","key":"bag","status":"done","msg":f"完成 {len(bags)}个大包"}): yield m

            # 装车
            vehicle=None
            if "vehicle" in steps and bags:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[装车] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"装车","key":"vehicle","status":"loading","msg":"执行中..."}): yield m
                plate=f"MN{datetime.now().strftime('%y%m%d')}{int(_time.time()*1000)}"
                r=await tms_post("/api/ProductPlanBillBasic/AddAndUpdateProductPlanBillBasicV2",{"countryCode":"MN","billLadingNo":plate,"remark":""})
                if not (r.get("state") or r.get("code") == 200):
                    async for m in sse("step",{"step":"装车","key":"vehicle","status":"fail","msg":"建车失败","errors":[{"result": r}]}): yield m
                    async for m in sse("error",{"message":"装车-建车失败","errors":[{"result": r}]}): yield m
                    return
                create_before = (datetime.now() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                await asyncio.sleep(1)
                cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                cur.execute(
                    "SELECT id FROM product_plan_bill_basic WHERE create_time > %s AND bill_lading_no=%s AND country_code='MN' ORDER BY id DESC LIMIT 1",
                    (create_before, plate)
                )
                row=cur.fetchone()
                if not row:
                    async for m in sse("step",{"step":"装车","key":"vehicle","status":"fail","msg":"未查到车辆ID"}): yield m
                    async for m in sse("error",{"message":f"装车-未查到车辆ID (after {create_before})"}): yield m
                    return
                vid=row[0]
                bag_nos=[b["bag_no"] for b in bags]
                r2=await tms_post("/api/ProductPlanBillBasic/AddProductPlanBillBasicSend",{"productPlanBillBasicId":vid,"sortingAreaPackagingNumberList":bag_nos,"customerCode":"Pdd-Mn"})
                if r2.get("state") or r2.get("code") == 200:
                    vehicle={"plate":plate,"vehicle_id":vid,"bag_count":len(bags)}
                    async for m in sse("step",{"step":"装车","key":"vehicle","status":"done","msg":f"车牌 {plate}"}): yield m
                else:
                    async for m in sse("step",{"step":"装车","key":"vehicle","status":"fail","msg":"包挂车失败","errors":[{"result": r2}]}): yield m
                    async for m in sse("error",{"message":"装车-包挂车失败","errors":[{"result": r2}]}): yield m
                    return

            # 发车
            if "dispatch" in steps and vehicle:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[发车] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"发车","key":"dispatch","status":"loading","msg":"执行中..."}): yield m
                async with httpx.AsyncClient(timeout=config.timeout) as c:
                    await c.get(f"{config.tms_host}/api/ProductPlanBillBasic/UpdateProductPlanBillBasicSetOffCar",params={"id":vehicle["vehicle_id"],"customerId":"13"},headers={"Authorization":f"Bearer {token}"})
                async for m in sse("step",{"step":"发车","key":"dispatch","status":"done","msg":"完成"}): yield m

            # 轨迹推送
            if route_ids and vehicle:
                if step_interval > 0:
                    async for m in sse("progress", {"msg": f"[轨迹] 等待 {step_interval}s 后开始..."}): yield m
                    await asyncio.sleep(step_interval)
                async for m in sse("step",{"step":"轨迹","key":"route","status":"loading","msg":f"推送{len(route_ids)}个节点..."}): yield m
                body = {"id":vehicle["vehicle_id"],"customerId":13,"isRemark":0,"remark":"","remarkEnglishName":"","remarkRussiaName":"","remarkKazakhstanName":"","billLadingNo":vehicle["plate"],"productPlanBillBasicId":vehicle["vehicle_id"]}
                ok_count = 0
                for rid in route_ids:
                    name = ROUTE_NODES.get(rid, str(rid))
                    async for m in sse("progress",{"msg":f"轨迹 {rid} {name} ..."}): yield m
                    body["customerRouteNodeId"] = rid
                    body["customerRoutingNodeChineseName"] = name
                    try:
                        import json as _j2
                        print(f"[ROUTE] body={_j2.dumps(body,ensure_ascii=False)}")
                        async with httpx.AsyncClient(timeout=config.timeout) as c:
                            rsp = await c.post(f"{config.tms_host}/api/TaoBaoProductPlan/TaoBaoCainiaoProductPlanAddRoute",
                                json=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
                            data_rsp = rsp.json()
                            if data_rsp.get("state") or data_rsp.get("code") == 200:
                                ok_count += 1
                                async for m in sse("progress",{"msg":f"  {rid} {name} OK"}): yield m
                            else:
                                async for m in sse("progress",{"msg":f"  {rid} {name} FAIL: {str(data_rsp)[:100]}"}): yield m
                    except Exception as ex:
                        async for m in sse("progress",{"msg":f"  {rid} {name} ERR: {ex}"}): yield m
                    await asyncio.sleep(1)
                async for m in sse("step",{"step":"轨迹","key":"route","status":"done","msg":f"完成 {ok_count}/{len(route_ids)}"}): yield m

            # 完成
            async for m in sse("done",{"orders":[{"index":o["index"],"mail_no":o["mail_no"],"ok":o["success"]} for o in orders],"bags":bags,"vehicle":vehicle}): yield m

        except Exception as e:
            async for m in sse("error", {"message": error_response(e).get("message", str(e)), "error_code": error_response(e).get("error_code", "UNKNOWN_ERROR")}): yield m
        finally:
            cur.close(); conn.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream; charset=utf-8")


async def _pdd_post_raw(body: dict[str, Any], path: str) -> dict[str, Any]:
    """PDD POST 辅助（用于批量）。"""
    from .sign_utils import sign_pdd
    config = PDDOrderConfig()
    sign = sign_pdd(body, config.client_secret)
    body_with_sign = {**body, "sign": sign}
    body_json = json.dumps(body_with_sign, ensure_ascii=False, separators=(",", ":"))
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.gateway_url}{path}",
                content=body_json.encode("utf-8"),
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
            result = rsp.json()
            return {"success": result.get("success", False), "data": result}
    except httpx.TimeoutException as e:
        logger.error("_pdd_post_raw_timeout", path=path, error=str(e))
        return {"success": False, "error_code": "TIMEOUT_ERROR", "message": f"请求PDD网关超时: {e}"}
    except httpx.HTTPError as e:
        logger.error("_pdd_post_raw_http_error", path=path, error_type=type(e).__name__, error=str(e))
        return {"success": False, "error_code": "NETWORK_ERROR", "message": f"网络错误: {type(e).__name__}: {e}"}
    except Exception as e:
        logger.error("_pdd_post_raw_error", path=path, error_type=type(e).__name__, error=str(e))
        return {"success": False, "error_code": "UNKNOWN_ERROR", "message": f"请求异常: {type(e).__name__}: {e}"}


async def _pdd_post(body: dict[str, Any], path: str, pp_code: str = "", step: str = "", tracking: str = "") -> dict[str, Any]:
    """通用 PDD POST（MD5 签名）。"""
    from .sign_utils import sign_pdd

    config = PDDOrderConfig()
    sign = sign_pdd(body, config.client_secret)
    body_with_sign = {**body, "sign": sign}
    import json as _json

    body_json = _json.dumps(body_with_sign, ensure_ascii=False, separators=(",", ":"))
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.gateway_url}{path}",
                content=body_json.encode("utf-8"),
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
            result = rsp.json()
            success = result.get("success", False)
            if step and tracking:
                update_order_status(tracking, step, "done" if success else "fail",
                                    "" if success else str(result.get("message", "")))
            resp = {"success": success, "data": result}
            if pp_code:
                resp["pp_code"] = pp_code
                resp["pp_code"] = pp_code
            return resp
    except Exception as e:
        return error_response(e)

