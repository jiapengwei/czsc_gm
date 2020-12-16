# coding: utf-8
from .base import BaseTraderM30, BaseTraderM5


class FutureTraderV1(BaseTraderM5):
    """FutureTickTraderV1a：5分钟笔同级别分解"""
    freqs = ["1分钟", "5分钟", "30分钟"]
    version = "FutureTraderV1a"

    def __init__(self, kg, bi_mode="new", max_count=300):
        super().__init__(kg, bi_mode, max_count)

    def long_open(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的开多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = s['5分钟_第N笔涨跌力度'] == "向下笔不创新低"
        c2 = s['5分钟_第N笔涨跌力度'] == "向下笔新低盘背"

        r1 = s['30分钟_第N笔涨跌力度'] in ["向下笔不创新低", "向下笔新低盘背"]

        right_a = s['1分钟_第N笔出井'] == '向下小井'
        left_a = s['1分钟_第N笔出井'] == '向下大井'

        if r1:
            if c1 and right_a:
                res['match'] = True
                res['desc'] = "满足开多情况一：5分钟向下笔不创新低（右侧）"

            if c1 and left_a:
                res['match'] = True
                res['desc'] = "满足开多情况二：5分钟向下笔不创新低（左侧）"

            if c2 and right_a:
                res['match'] = True
                res['desc'] = "满足开多情况三：5分钟向下笔新低盘背（右侧）"

            if c2 and left_a:
                res['match'] = True
                res['desc'] = "满足开多情况四：5分钟向下笔新低盘背（左侧）"

        if res['match']:
            self.cache['long_open_price'] = s["latest_price"]
        return res

    def long_close(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的平多仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c = "向上" in s['5分钟_第N笔涨跌力度']

        right_a = s['1分钟_第N笔出井'] == '向上小井'
        left_a = s['1分钟_第N笔出井'] == '向上大井' and s['5分钟_最近三根无包含K线形态'] == 'up'

        if c and right_a:
            res['match'] = True
            res['desc'] = "满足平多情况一：5分钟向上笔结束（右侧）"

        if c and left_a:
            res['match'] = True
            res['desc'] = "满足平多情况二：5分钟向上笔结束（左侧）"

        if res['match']:
            self.cache['long_open_price'] = 0
        return res

    def short_open(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的开空仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c1 = s['5分钟_第N笔涨跌力度'] == "向上笔不创新高"
        c2 = s['5分钟_第N笔涨跌力度'] == "向上笔新高盘背"

        r1 = s['30分钟_第N笔涨跌力度'] in ["向上笔不创新高", "向上笔新高盘背"] and not s['30分钟_第N笔向上新高']

        right_a = s['1分钟_第N笔出井'] == '向上小井'
        left_a = s['1分钟_第N笔出井'] == '向上大井'

        if r1:
            if c1 and right_a:
                res['match'] = True
                res['desc'] = "满足开空情况一：5分钟向上笔不创新高（右侧）"

            if c1 and left_a:
                res['match'] = True
                res['desc'] = "满足开空情况二：5分钟向上笔不创新高（左侧）"

            if c2 and right_a:
                res['match'] = True
                res['desc'] = "满足开空情况三：5分钟向上笔新高盘背（右侧）"

            if c2 and left_a:
                res['match'] = True
                res['desc'] = "满足开空情况四：5分钟向上笔新高盘背（左侧）"

        if res['match']:
            self.cache['short_open_price'] = s["latest_price"]
        return res

    def short_close(self):
        s = self.s
        res = {"match": False, "desc": "没有满足的平空仓条件", "trader": self.version,
               "symbol": self.symbol, "dt": self.end_dt, "price": self.latest_price}

        c = "向下" in s['5分钟_第N笔涨跌力度']

        right_a = s['1分钟_第N笔出井'] == '向下小井'
        left_a = s['1分钟_第N笔出井'] == '向下大井'

        if c and right_a:
            res['match'] = True
            res['desc'] = "满足平空情况一：5分钟向下笔结束（右侧）"

        if c and left_a:
            res['match'] = True
            res['desc'] = "满足平空情况二：5分钟向下笔结束（左侧）"

        if res['match']:
            self.cache['short_open_price'] = 0
        return res


