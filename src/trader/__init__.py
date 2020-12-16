# coding: utf-8
"""
.share 中实现股票相关的策略

.future 中实现期货相关的策略

"""

from .share import ShareTraderV1
from .share import ShareTraderV2
from .share import ShareTraderV3
from .future import FutureTraderV1

# 所有实现的策略，都需要注册到 traders ，否则无法通过 traders 直接获取
traders = {
    "ShareTraderV1": ShareTraderV1,
    "ShareTraderV2": ShareTraderV2,
    "ShareTraderV3": ShareTraderV3,
    "FutureTraderV1": FutureTraderV1,
}

