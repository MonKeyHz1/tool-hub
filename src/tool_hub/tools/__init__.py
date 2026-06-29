"""工具包的初始化，负责自动发现和注册所有工具。

每新增一个工具，只需在此导入并调用 registry.register() 即可。
"""

from .. import registry
from ..logging import setup_logging

# 初始化日志
setup_logging()

# ==============================================================
# 所有工具的注册入口
# 新增工具时，按以下格式添加：
#   from .新工具包 import NewTool
#   registry.register(NewTool())
# ==============================================================

from .mip_customs import MIPCustomsTool  # noqa: E402
from .temu_gateway import TemuGatewayTool  # noqa: E402
from .pdd_order import PDDOrderTool  # noqa: E402
from .encoding_converter import EncodingConverterTool  # noqa: E402
from .push_weight import PushWeightTool  # noqa: E402
from .financial_system import FinancialSystemTool  # noqa: E402

# 注册 MIP 海关清关工具（拆为创建和更新两个）
# 注册 MIP 海关清关工具（主页显示一个卡片，内部 Tab 拆创建/更新）
registry.register(MIPCustomsTool(use_create=True, tool_id="mip_customs_create", tool_name="MIP海关清关-创建", hidden=True))
registry.register(MIPCustomsTool(use_create=False, tool_id="mip_customs_update", tool_name="MIP海关清关-更新", hidden=True))
registry.register(MIPCustomsTool(use_create=True, tool_id="mip_customs_clearance", tool_name="MIP海关清关"))
# 注册 Temu 网关工具
registry.register(TemuGatewayTool())
# 注册 PDD-MN流程工具
registry.register(PDDOrderTool())
# 注册编码转换工具
registry.register(EncodingConverterTool())
# 注册推送重量工具
registry.register(PushWeightTool())
# 注册财务系统工具
registry.register(FinancialSystemTool())
