# coding: utf-8
from gm.api import *
from datetime import datetime, timedelta
from collections import OrderedDict
import traceback
import pandas as pd
import requests
from czsc.utils.kline_generator import KlineGeneratorByTick, KlineGeneratorBy1Min
import os
from .conf import gm_token

set_token(gm_token)

freq_map = {"60s": "1分钟", "300s": "5分钟", "900s": "15分钟",
            "1800s": "30分钟", "3600s": "60分钟", "1d": "日线"}

indices = {
    "上证指数": 'SHSE.000001',
    "创业板指数": 'SZSE.399006',
    "上证50": 'SHSE.000016',
    "深证成指": "SZSE.399001",
    "沪深300": "SHSE.000300",
    "深次新股": "SZSE.399678",
    "中小板指": "SZSE.399005",
}

def create_logger(log_file, name='logger', cmd=True, level="info"):
    """define a logger for your program

    parameters
    ------------
    log_file     file name of log
    name         name of logger

    example
    ------------
    logger = create_logger('example.log',name='logger',)
    logger.info('This is an example!')
    logger.warning('This is a warn!')

    """
    import logging

    level_map = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "error": logging.ERROR,
    }
    log_level = level_map.get(level, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # set format
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    # file handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # cmd handler
    if cmd:
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def get_index_shares(name, end_date):
    """获取某一交易日的指数成分股列表

    symbols = get_index_shares("上证50", "2019-01-01 09:30:00")
    """
    end_date = end_date.split(" ")[0]
    constituents = get_history_constituents(indices[name], end_date, end_date)[0]
    symbol_list = [k for k, v in constituents['constituents'].items()]
    return list(set(symbol_list))


def push_msg(msg_type, content, key):
    """推送消息到企业微信群

    content格式参考： https://work.weixin.qq.com/api/doc/90000/90136/91770
    """
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    data = {"msgtype": msg_type, msg_type: content}
    response = requests.post(api_send, json=data)
    try:
        assert response.json()['errmsg'] == 'ok'
    except:
        print("消息推送失败")


def push_file(file, file_name=None, key=None):
    """推送文件到企业微信"""
    api_upload = "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={}&type=file".format(key)
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    if not file_name:
        file_name = os.path.split(file)[1]
    assert key, "没有设置 key"
    try:
        files = {file_name: open(file, 'rb').read()}
        r1 = requests.post(api_upload, files=files)
        mid = r1.json()['media_id']
        assert r1.json()['errmsg'] == 'ok'

        data = {"msgtype": "file", "file": {"media_id": mid}}
        r2 = requests.post(api_send, json=data)
        assert r2.json()['errmsg'] == 'ok'
    except:
        print("消息推送失败")


def get_contract_basic(symbol, trade_date=None):
    """获取合约信息

    https://www.myquant.cn/docs/python/python_select_api#8ba2064987fb1d1f

    https://www.myquant.cn/docs/python/python_select_api#8f28e1de81b80633
    """
    if not trade_date:
        res = get_instruments(symbol)
        if not res:
            return None
        return res[0]
    else:
        res = None


# ======================================================================================================================

def report_account_status(context):
    """报告账户持仓状态"""
    logger = context.logger
    latest_dt = context.now.strftime(r"%Y-%m-%d %H:%M:%S")
    logger.info("=" * 30 + f" 账户状态【{latest_dt}】 " + "=" * 30)

    account = context.account()
    cash = account.cash
    positions = account.positions(symbol="", side="")

    cash_report = f"净值：{int(cash.nav)}，可用资金：{int(cash.available)}，" \
                  f"浮动盈亏：{int(cash.fpnl)}，标的数量：{len(positions)}"
    logger.info(cash_report)

    for p in positions:
        p_report = f"持仓标的：{p.symbol}，数量：{p.volume}，成本：{round(p.vwap, 2)}，方向：{p.side}，" \
                   f"当前价：{round(p.price, 2)}，成本市值：{int(p.volume * p.vwap)}"
        logger.info(p_report)


def on_order_status(context, order):
    """
    https://www.myquant.cn/docs/python/python_object_trade#007ae8f5c7ec5298

    :param context:
    :param order:
    :return:
    """
    latest_dt = context.now.strftime("%Y-%m-%d %H:%M:%S")
    logger = context.logger
    file_orders = context.file_orders
    msg = f"订单状态更新通知：交易时间：{latest_dt}，订单状态：{order.symbol}，方向：{order.side}，" \
          f"价格：{round(order.price, 2)}，状态：{order.status}，" \
          f"委托量：{int(order.volume)}，已成量: {int(order.filled_volume)}，" \
          f"成交均价：{round(order.filled_vwap, 2)}"

    logger.info(msg)
    if context.mode == MODE_BACKTEST:
        with open(file_orders, 'a', encoding="utf-8") as f:
            f.write(str(order) + '\n')
    else:
        if order.status in [1, 3]:
            push_msg(msg_type="text", content={"content": str(msg)}, key=context.wx_key)


def on_execution_report(context, execrpt):
    """响应委托被执行事件，委托成交或者撤单拒绝后被触发。

    https://www.myquant.cn/docs/python/python_trade_event#on_execution_report%20-%20%E5%A7%94%E6%89%98%E6%89%A7%E8%A1%8C%E5%9B%9E%E6%8A%A5%E4%BA%8B%E4%BB%B6
    https://www.myquant.cn/docs/python/python_object_trade#ExecRpt%20-%20%E5%9B%9E%E6%8A%A5%E5%AF%B9%E8%B1%A1

    :param context:
    :param execrpt:
    :return:
    """
    latest_dt = context.now.strftime("%Y-%m-%d %H:%M:%S")
    logger = context.logger
    msg = f"委托订单被执行通知：时间：{latest_dt}，标的：{execrpt.symbol}，方向：{execrpt.side}，" \
          f"成交量: {int(execrpt.volume)}，成交价：{round(execrpt.price, 2)}，执行回报类型：{execrpt.exec_type}"

    logger.info(msg)
    if context.mode != MODE_BACKTEST:
        push_msg(msg_type="text", content={"content": str(msg)}, key=context.wx_key)


def on_backtest_finished(context, indicator):
    """

    :param context:
    :param indicator:
        https://www.myquant.cn/docs/python/python_object_trade#bd7f5adf22081af5
    :return:
    """
    logger = context.logger
    logger.info(str(indicator))
    logger.info("回测结束 ... ")
    cash = context.account().cash

    for k, v in indicator.items():
        if isinstance(v, float):
            indicator[k] = round(v, 4)

    symbol = list(context.symbols)[0]
    row = OrderedDict({
        "操盘手": context.symbols_map[symbol]['trader'].version,
        "研究标的": ", ".join(list(context.symbols_map.keys())),
        "回测开始时间": context.backtest_start_time,
        "回测结束时间": context.backtest_end_time,
        "累计收益率": indicator['pnl_ratio'],
        "最大回撤": indicator['max_drawdown'],
        "年化收益率": indicator['pnl_ratio_annual'],
        "夏普比率": indicator['sharp_ratio'],
        "盈利次数": indicator['win_count'],
        "亏损次数": indicator['lose_count'],
        "交易胜率": indicator['win_ratio'],
        "累计出入金": int(cash['cum_inout']),
        "累计交易额": int(cash['cum_trade']),
        "累计手续费": int(cash['cum_commission']),
        "累计平仓收益": int(cash['cum_pnl']),
        "净收益": int(cash['pnl']),
    })
    df = pd.DataFrame([row])
    df.to_excel(os.path.join(context.data_path, "回测结果.xlsx"), index=False)
    logger.info("回测结果：{}".format(row))
    content = ""
    for k, v in row.items():
        content += "{}: {}\n".format(k, v)

    for symbol in context.symbols:
        # 转换信号到 excel 文件中
        file_s = os.path.join(context.cache_path, "{}_signals.txt".format(symbol))
        lines = [eval(x) for x in open(file_s, 'r', encoding="utf-8").read().strip().split("\n")]
        df = pd.DataFrame(lines)
        df.to_excel(file_s.replace(".txt", ".xlsx"), index=False)
        os.remove(file_s)

        # 查看买卖详情
        file_bs = os.path.join(context.cache_path, "{}_bs.txt".format(symbol))
        if os.path.exists(file_bs):
            lines = [eval(x) for x in open(file_bs, 'r', encoding="utf-8").read().strip().split("\n")]
            df = pd.DataFrame(lines)
            print(symbol, "\n", df.desc.value_counts())
            print(df)

    try:
        push_msg(msg_type='text', content={"content": content}, key=context.wx_key)
    except:
        traceback.print_exc()

def on_error(context, code, info):
    logger = context.logger
    msg = "{} - {}".format(code, info)
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        push_msg(msg_type="text", content={"content": msg}, key=context.wx_key)


def on_account_status(context, account):
    """响应交易账户状态更新事件，交易账户状态变化时被触发"""
    context.logger.info(str(account))


# ======================================================================================================================

def format_kline(df):
    df['dt'] = df['eob']
    df['vol'] = df['volume']
    if "position" in df.columns:
        df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'position']]
    else:
        df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        df.loc[:, col] = df[col].apply(lambda x: round(x, 2))
    return df


def get_kline(symbol, end_time, freq='60s', count=33000):
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(r"%Y-%m-%d %H:%M:%S")

    exchange = symbol.split(".")[0]

    if exchange in ["SZSE", "SHSE"]:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time,
                       fields='symbol,eob,open,close,high,low,volume',
                       count=count, df=True, adjust=1)
    else:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time,
                       fields='symbol,eob,open,close,high,low,volume,position',
                       count=count, df=True, adjust=1)
    return format_kline(df)


def format_tick(tick):
    k = {'symbol': tick['symbol'],
         'dt': tick['created_at'],
         'price': tick['price'],
         'vol': tick['last_volume']}
    return k


def get_ticks(symbol, end_time, count=33000):
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(r"%Y-%m-%d %H:%M:%S")
    data = history_n(symbol=symbol, frequency="tick", end_time=end_time, count=count, df=False, adjust=1)
    return data


def download_1min(symbol, start_time, end_time):
    """

    :param symbol:
    :param start_time:
    :param end_time:
    :return:

    example:

    >>> symbol = "SZSE.300033"
    >>> start_time = datetime.strptime("2017-01-01", "%Y-%m-%d")
    >>> end_time = datetime.strptime("2020-01-01", "%Y-%m-%d")
    >>> download_1min(symbol, start_time, end_time)
    """
    data = []
    end_time_ = start_time + timedelta(days=120)
    while 1:
        print(f"get 1min of {symbol}: {end_time_}")
        df_ = get_kline(symbol, end_time_, freq='60s', count=33000)
        if not df_.empty:
            data.append(df_)
        if end_time_ > end_time:
            break
        else:
            end_time_ += timedelta(days=120)

    df = pd.concat(data)
    df.drop_duplicates(inplace=True)
    df.sort_values('dt', inplace=True)
    df['dt'] = pd.to_datetime(df['dt']).apply(lambda x: x.replace(tzinfo=None))
    df = df[df.dt <= end_time]
    df.reset_index(drop=True, inplace=True)
    return df


# ======================================================================================================================

def is_order_exist(context, symbol, side, position_effect) -> bool:
    """判断同类型订单是否已经存在

    :param context:
    :param symbol: 交易标的
    :param side: 交易方向
    :param position_effect: 开平标志
    :return: bool
    """
    uo = context.unfinished_orders
    if not uo:
        return False
    else:
        for o in uo:
            if o.symbol == symbol and o.side == side and o.position_effect == position_effect:
                context.logger.info("同类型订单已存在：{} - {} - {}".format(symbol, side, position_effect))
                return True
    return False

def write_bs(context, symbol, bs):
    """把bs详细信息写入文本文件"""
    file_bs = os.path.join(context.cache_path, "{}_bs.txt".format(symbol))
    with open(file_bs, 'a', encoding="utf-8") as f:
        row = dict(bs)
        row['dt'] = row['dt'].strftime("%Y-%m-%d %H:%M:%S")
        f.write(str(row) + "\n")

def take_snapshot(context, trader, name):
    """

    :param context:
    :param trader:
    :param name: str
        平多、平空、开多、开空、快照
    :return:
    """
    symbol = trader.symbol
    now_ = context.now.strftime('%Y%m%d%H%M')
    price = trader.latest_price
    file_html = os.path.join(context.cache_path, f"{symbol}{name}_{price}_{now_}.html")
    trader.take_snapshot(file_html, width="1400px", height="580px")
    if context.mode != MODE_BACKTEST:
        file_name = "{}_{}_{}.html".format(symbol.split(".")[1], trader.latest_price, now_)
        push_file(file_html, file_name, key=context.wx_key)


def adjust_future_position(context, symbol, trader):
    """调整单只期货标的仓位"""
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.future_id)

    # 判断是否需要平多仓
    long_position = account.positions(symbol=symbol, side=PositionSide_Long)
    if long_position:
        lp = long_position[0].available
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Close)
        res = trader.long_close()
        if not oe and lp > 0 and res['match']:
            context.logger.info("{} - 平多 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name="平多_{}".format(res['desc']))

    # 判断是否需要平空仓
    short_position = account.positions(symbol=symbol, side=PositionSide_Short)
    if short_position:
        sp = short_position[0].available
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Close)
        res = trader.short_close()
        if not oe and sp > 0 and res['match']:
            context.logger.info("{} - 平空 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            order_volume(symbol=symbol, volume=sp, side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name="平空_{}".format(res['desc']))

    # 判断是否需要开仓
    mp = context.symbols_map[symbol]['mp']
    res = trader.long_open()
    if not long_position and res['match']:
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Open)
        if not oe:
            context.logger.info("{} - 开多 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            if mp > 1:
                order_volume(symbol=symbol, volume=mp, side=OrderSide_Buy, order_type=OrderType_Market,
                             position_effect=PositionEffect_Open, account=account.id)
            else:
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Long,
                                     order_type=OrderType_Market, account=account.id)
            take_snapshot(context, trader, name="开多_{}".format(res['desc']))

    res = trader.short_open()
    if not short_position and res['match']:
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Open)
        if not oe:
            context.logger.info("{} - 开空 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            if mp > 1:
                order_volume(symbol=symbol, volume=mp, side=OrderSide_Sell, order_type=OrderType_Market,
                             position_effect=PositionEffect_Open, account=account.id)
            else:
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Short,
                                     order_type=OrderType_Market, account=account.id)
            take_snapshot(context, trader, name="开空_{}".format(res['desc']))


def adjust_share_position(context, symbol, trader):
    """调整单只标的仓位"""
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.share_id)

    long_position = account.positions(symbol=symbol, side=PositionSide_Long)
    if long_position:
        # 判断是否需要平多仓
        lp = long_position[0].volume - long_position[0].volume_today
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Close)
        in_trade_time = "14:59" > context.now.strftime("%H:%M") > "09:31"
        res = trader.long_close()
        if not oe and lp > 0 and res['match'] and in_trade_time:
            context.logger.info("{} - 平多 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name="平多_{}".format(res['desc']))
    else:
        # 判断是否需要开多仓
        mp = context.symbols_map[symbol]['mp']
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Open)
        in_trade_time = "14:59" > context.now.strftime("%H:%M") > "09:31"
        res = trader.long_open()
        if not oe and res['match'] and in_trade_time:
            context.logger.info("{} - 开多 - {}".format(symbol, res['desc']))
            write_bs(context, symbol, res)
            if mp > 1:
                order_volume(symbol=symbol, volume=mp * 100, side=OrderSide_Buy, order_type=OrderType_Market,
                             position_effect=PositionEffect_Open, account=account.id)
            else:
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Long,
                                     order_type=OrderType_Market, account=account.id)
            take_snapshot(context, trader, name="开多_{}".format(res['desc']))

def get_init_kg(context, symbol, generator: [KlineGeneratorByTick, KlineGeneratorBy1Min],
                freqs=('1分钟', '5分钟', "30分钟", "日线"), max_count=1000):
    """获取symbol的初始化kline generator"""
    freq_map_ = {"1分钟": '60s', "5分钟": '300s', "15分钟": '900s', "30分钟": '1800s', "日线": '1d'}

    if context.mode == MODE_BACKTEST:
        end_time = context.now
    else:
        end_time = context.now - timedelta(days=1)
        end_time = end_time.replace(hour=16, minute=0)

    kg = generator(max_count=max_count, freqs=freqs)

    for freq in freqs:
        df = get_kline(symbol=symbol, end_time=end_time, freq=freq_map_[freq], count=max_count)
        kg.init_kline(freq=freq, kline=df.to_dict("records"))

    if context.mode != MODE_BACKTEST:
        if isinstance(kg, KlineGeneratorBy1Min):
            bars = get_kline(symbol=symbol, end_time=context.now, freq="60s", count=300)
            data = [x for x in bars.to_dict("records") if x['dt'] > end_time]
        elif isinstance(kg, KlineGeneratorByTick):
            ticks = get_ticks(symbol=symbol, end_time=context.now, count=3000)
            ticks = [format_tick(x) for x in ticks]
            data = [x for x in ticks if x['dt'] > end_time]
        else:
            raise ValueError

        if data:
            print("更新 kg 至实盘最新状态，共有{}行数据需要update".format(len(data)))
            for row in data:
                kg.update(row)
    return kg
