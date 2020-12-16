# coding: utf-8
from .base import BaseTraderD, BaseTraderM30

# ======================================================================================================================

class ShareTraderV1(BaseTraderD):
    """ShareTraderV1a：日线笔同级别分解操作"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "ShareTraderV1"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)

    def long_open(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的开多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = s['日线_第N笔涨跌力度'] == '向下笔不创新低'
        c2 = s['日线_第N-1笔涨跌力度'] in ['向下笔新低盘背', '向下笔不创新低']

        left_a = s['30分钟_第N笔涨跌力度'] == '向下笔新低盘背'
        left_b = s['5分钟_第N笔涨跌力度'] == '向下笔不创新低'

        right_a = s['30分钟_第N笔涨跌力度'] == '向下笔不创新低'
        right_b = s['5分钟_第N笔第三买卖'] == "三买"

        if c1 and right_a:
            res['match'] = True
            res['desc'] = "满足开多情况一：日线第N笔向下不创新低（右侧）"

        if c1 and left_a:
            res['match'] = True
            res['desc'] = "满足开多情况二：日线第N笔向下不创新低（左侧）"

        if c2 and right_a and right_b:
            res['match'] = True
            res['desc'] = "满足开多情况三：日线第N笔向上延伸（右侧）"

        if c2 and left_a and left_b:
            res['match'] = True
            res['desc'] = "满足开多情况四：日线第N笔向上延伸（左侧）"

        if res['match']:
            self.cache['long_open_price'] = s["latest_price"]
        return res

    def long_close(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的平多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = "向上" in s['日线_第N笔涨跌力度']
        c2 = s['latest_price'] < self.cache.get('long_open_price', 0) * 0.99

        left_a = s['30分钟_第N笔涨跌力度'] == '向上笔新高盘背'
        right_a = s['30分钟_第N笔涨跌力度'] == '向上笔不创新高'

        if c1 and left_a:
            res['match'] = True
            res['desc'] = "满足平多情况一：日线第N笔向上结束（左侧）"

        if c1 and right_a:
            res['match'] = True
            res['desc'] = "满足平多情况二：日线第N笔向上结束（右侧）"

        if c2 and right_a:
            res['match'] = True
            res['desc'] = "满足平多情况三：30分钟第N笔不创新高（止损）"

        if res['match']:
            self.cache['long_open_price'] = 0
        return res


class ShareTraderV2(BaseTraderD):
    """ShareTraderV2a：指数增强策略"""
    freqs = ["1分钟", "5分钟", "15分钟", "30分钟", "日线"]
    version = "ShareTraderV2"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)

    def long_score(self):
        """计算多头表现得分

        :return:
        """
        s = self.s
        score = 100

        sc1 = s['5分钟_第N笔结束标记的上边沿'] < s['日线_第N笔结束标记的下边沿'] and "向上" in s['日线_第N笔涨跌力度']
        sc2 = s['1分钟_第N笔结束标记的上边沿'] < s['30分钟_第N笔结束标记的下边沿'] and "向上" in s['30分钟_第N笔涨跌力度']
        sc3 = s['30分钟_第N笔涨跌力度'] in ['向上笔不创新高', '向上笔新高盘背'] and not s['30分钟_第N笔向上新高']
        sc4 = s['日线_第N笔涨跌力度'] in ['向上笔不创新高', '向上笔新高盘背'] and not s['日线_第N笔向上新高']
        sc5 = s['日线_第N笔涨跌力度'] == "向下笔新低无背" or s['日线_第N-1笔涨跌力度'] == "向下笔新低无背"
        sc6 = s['5分钟_第N笔出井'] in ['向上小井', '向上大井']

        if sc1 or sc2 or sc3 or sc4 or sc5 or sc6:
            score -= 100

        bc1 = s['5分钟_第N笔结束标记的下边沿'] > s['日线_第N笔结束标记的上边沿'] and "向下" in s['日线_第N笔涨跌力度']
        bc2 = s['1分钟_第N笔结束标记的下边沿'] > s['30分钟_第N笔结束标记的上边沿'] and "向下" in s['30分钟_第N笔涨跌力度']
        bc3 = s['30分钟_第N笔涨跌力度'] in ['向下笔不创新低', '向下笔新低盘背'] and not s['30分钟_第N笔向下新低']
        bc4 = s['日线_第N笔涨跌力度'] in ['向下笔不创新低', '向下笔新低盘背'] and not s['日线_第N笔向下新低']
        bc5 = s['日线_第N笔涨跌力度'] == "向下笔新高无背" or s['日线_第N-1笔涨跌力度'] == "向下笔新高无背"
        bc6 = s['5分钟_第N笔出井'] in ['向下小井', '向下大井']

        if bc1 or bc2 or bc3 or bc4 or bc5 or bc6:
            score += 100

        return max(score, 0)


class ShareTraderV3(BaseTraderM30):
    """ShareTraderV3a：30分钟笔同级别分解操作"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "ShareTraderV3"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)

    def long_open(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的开多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = s['30分钟_第N笔涨跌力度'] == '向下笔不创新低'
        c2 = s['30分钟_第N笔涨跌力度'] == '向下笔新低盘背'

        r1 = s['1分钟_第N笔涨跌力度'] == '向下笔不创新低'

        left_a = s['5分钟_第N笔涨跌力度'] == '向下笔新低盘背'
        left_b = s['5分钟_第N笔出井'] == "向下大井"

        right_a = s['5分钟_第N笔涨跌力度'] == '向下笔不创新低'

        if c1 and right_a and r1:
            res['match'] = True
            res['desc'] = "满足开多情况一：30分钟第N笔向下不创新低（右侧）"

        if c1 and (left_a or left_b) and r1:
            res['match'] = True
            res['desc'] = "满足开多情况二：30分钟第N笔向下不创新低（左侧）"

        if c2 and right_a and r1:
            res['match'] = True
            res['desc'] = "满足开多情况三：30分钟第N笔向下笔新低盘背（右侧）"

        if c2 and (left_a or left_b) and r1:
            res['match'] = True
            res['desc'] = "满足开多情况四：30分钟第N笔向下笔新低盘背（左侧）"

        if res['match']:
            self.cache['long_open_price'] = s["latest_price"]
        return res

    def long_close(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的平多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = s['30分钟_第N笔涨跌力度'] == '向上笔不创新高'
        c2 = s['30分钟_第N笔涨跌力度'] == '向上笔新高盘背'

        r1 = s['1分钟_第N笔涨跌力度'] == '向上笔不创新高'

        left_a = s['5分钟_第N笔涨跌力度'] == '向上笔新高盘背'
        left_b = s['5分钟_第N笔出井'] == "向上大井"

        right_a = s['5分钟_第N笔涨跌力度'] == '向上笔不创新高'

        if c1 and right_a and r1:
            res['match'] = True
            res['desc'] = "满足平多情况一：30分钟第N笔向上笔不创新高（右侧）"

        if c1 and (left_a or left_b) and r1:
            res['match'] = True
            res['desc'] = "满足平多情况二：30分钟第N笔向上笔不创新高（左侧）"

        if c2 and right_a and r1:
            res['match'] = True
            res['desc'] = "满足平多情况三：30分钟第N笔向上笔新高盘背（右侧）"

        if c2 and (left_a or left_b) and r1:
            res['match'] = True
            res['desc'] = "满足平多情况四：30分钟第N笔向上笔新高盘背（左侧）"

        if res['match']:
            self.cache['long_open_price'] = 0
        return res
