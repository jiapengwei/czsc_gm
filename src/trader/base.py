# coding: utf-8
from czsc.utils.kline_generator import KlineGeneratorByTick, KlineGeneratorBy1Min
from czsc.signals import KlineSignals
from czsc.utils.plot import ka_to_echarts
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts


class BaseTrader:
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "BaseTrader@20201210"

    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min], bi_mode="new", max_count=300):
        """
        :param kg: 基于tick或1分钟的K线合成器
        """
        assert "1分钟" in self.freqs, "必须使用1分钟级别"
        self.kg = kg
        klines = self.kg.get_klines({k: max_count for k in self.freqs})
        self.kas = {k: KlineSignals(klines[k], name=k, bi_mode=bi_mode,  max_count=max_count,
                                    use_xd=False, use_ta=False) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price
        self.positions = dict()
        self.s = self._signals()
        self.cache = dict()
        self.kg_updated = False

    def take_snapshot(self, file_html, width="950px", height="480px"):
        """获取交易快照

        :param file_html:
        :param width:
        :param height:
        :return:
        """
        tab = Tab(page_title="{}的交易快照@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = ka_to_echarts(self.kas[freq], width, height)
            tab.add(chart, freq)

        headers = ["名称", "数据"]
        rows = [[k, v] for k, v in self.s.items()]
        table = Table()
        table.add(headers, rows)
        table.set_global_opts(title_opts=ComponentTitleOpts(title="缠论信号", subtitle=""))
        tab.add(table, "信号表")
        tab.render(file_html)

    def _signals(self):
        """计算交易决策需要的状态信息"""
        s = {"symbol": self.symbol, "dt": self.end_dt, "latest_price": self.latest_price}

        for freq, ks in self.kas.items():
            if freq in ["日线", '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(ks.get_signals())

        s['1分钟最近三根K线站稳5分钟第N笔上沿'] = False
        s['1分钟最近三根K线跌破5分钟第N笔下沿'] = False
        ks1m = self.kas['1分钟']
        tri_1mk = ks1m.kline_raw[-3:]
        if sum([x['low'] > s['5分钟_第N笔结束标记的上边沿'] for x in tri_1mk]) == 3:
            s['1分钟最近三根K线站稳5分钟第N笔上沿'] = True
        if sum([x['high'] < s['5分钟_第N笔结束标记的下边沿'] for x in tri_1mk]) == 3:
            s['1分钟最近三根K线跌破5分钟第N笔下沿'] = True

        return s

    def update_kg(self, data):
        """输入最新的ticks或1分钟K线，更新 KlineGenerator"""
        for row in data:
            self.kg.update(row)
        self.kg_updated = True

    def update_signals(self):
        """更新信号，必须先调用 update_kg 方法更新 KlineGenerator"""
        assert self.kg_updated, "更新信号前，必须先调用 update_kg 方法更新 KlineGenerator"
        klines_one = self.kg.get_klines({k: 1 for k in self.freqs})
        for freq, klines_ in klines_one.items():
            k = klines_[-1]
            self.kas[freq].update(k)

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price
        self.s = self._signals()
        self.kg_updated = False


class BaseTraderD(BaseTrader):
    """BaseTraderD：日线策略基类"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "BaseTraderD"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)
        assert "5分钟" in self.freqs

    def is_decision_point(self):
        """输入一行特征，判断是否是决策点，作为数据过滤标准"""
        row = self.s
        up_dp = row['30分钟_最近三根无包含K线形态'] in ['d', 'up'] and "向下" in row['30分钟_第N笔涨跌力度']
        dn_dp = row['30分钟_最近三根无包含K线形态'] in ['g', 'down'] and "向上" in row['30分钟_第N笔涨跌力度']

        if up_dp or dn_dp:
            return True
        else:
            return False

class BaseTraderM30(BaseTrader):
    """BaseTraderM30：30分钟策略基类"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "BaseTraderM30"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)
        assert "1分钟" in self.freqs

    def is_decision_point(self):
        """输入一行特征，判断是否是决策点，作为数据过滤标准"""
        row = self.s
        up_dp = row['5分钟_最近三根无包含K线形态'] in ['d', 'up'] and "向下" in row['5分钟_第N笔涨跌力度']
        dn_dp = row['5分钟_最近三根无包含K线形态'] in ['g', 'down'] and "向上" in row['5分钟_第N笔涨跌力度']

        if up_dp or dn_dp:
            return True
        else:
            return False

class BaseTraderM5(BaseTrader):
    """BaseTraderM5：5分钟策略基类"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    version = "BaseTraderM5"

    def __init__(self, kg, bi_mode="new", max_count=500):
        super().__init__(kg, bi_mode, max_count)
        assert "1分钟" in self.freqs

    def is_decision_point(self):
        """输入一行特征，判断是否是决策点，作为数据过滤标准"""
        row = self.s
        up_dp = row['1分钟_最近三根无包含K线形态'] in ['d', 'up'] and "向下" in row['1分钟_第N笔涨跌力度']
        dn_dp = row['1分钟_最近三根无包含K线形态'] in ['g', 'down'] and "向上" in row['1分钟_第N笔涨跌力度']

        if up_dp or dn_dp:
            return True
        else:
            return False


