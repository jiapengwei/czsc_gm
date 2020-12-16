# coding: utf-8
from src.gm_utils import *
from src.trader import traders
from src import conf


def adjust_position(context, symbol):
    bars = context.data(symbol=symbol, frequency='60s', count=5, fields='symbol,eob,open,close,high,low,volume')
    trader = context.symbols_map[symbol]['trader']
    bars = format_kline(bars)
    bars = bars.to_dict("records")
    bars_new = [x for x in bars if x['dt'] > trader.kg.end_dt]
    if bars_new:
        trader.update_kg(bars_new)
        trader.update_signals()
    context.symbols_map[symbol]['trader'] = trader
    context.desc = str(context.symbols_map)

    if not trader.is_decision_point():
        return

    last_bar = bars_new[-1]
    if context.mode == MODE_BACKTEST:
        if last_bar['dt'].hour == 14 and last_bar['dt'].minute == 30:
            print("{} - {} - {}".format(trader.s['symbol'], trader.s['dt'], trader.s['latest_price']))
    else:
        if last_bar['dt'].minute % 30 == 0:
            print("{} - {} - {}".format(trader.s['symbol'], trader.s['dt'], trader.s['latest_price']))
            take_snapshot(context, trader, name='快照')

    file_s = os.path.join(context.cache_path, "{}_signals.txt".format(symbol))
    with open(file_s, 'a', encoding="utf-8") as f:
        row = dict(trader.s)
        row['dt'] = row['dt'].strftime("%Y-%m-%d %H:%M:%S")
        f.write(str(row) + "\n")

    exchange = symbol.split(".")[0]
    if exchange in ["SZSE", "SHSE"]:
        adjust_share_position(context, symbol, trader)
    else:
        adjust_future_position(context, symbol, trader)


def init(context):
    if context.mode == MODE_BACKTEST:
        data_path = "logs/1min_{}".format(datetime.now().strftime("%Y%m%d%H%M%S"))
    else:
        data_path = "logs/trader"
    context.wx_key = conf.wx_token
    context.share_id = conf.share_account_id    # 股票账户ID
    context.future_id = conf.future_account_id  # 期货账户ID

    cache_path = os.path.join(data_path, "cache")
    if not os.path.exists(data_path):
        os.makedirs(cache_path)
    context.logger = create_logger(os.path.join(data_path, "backtest.log"), cmd=True, name="gm")
    context.data_path = data_path
    context.cache_path = cache_path
    context.file_orders = os.path.join(data_path, "orders.txt")

    # 交易标的配置：mp 为最大持仓量，小于1，按百分比计算，大于1，表示交易手数
    # 支持同时对股票和期货进行交易
    symbols_map = {
        "CFFEX.IH2010": {"mp": 20, "trader": "FutureTraderV1"},
        "SZSE.000795": {"mp": 0.998, "trader": "ShareTraderV3"},
    }

    subscribe(",".join(symbols_map.keys()), frequency='60s', count=300, wait_group=True, wait_group_timeout="300s")

    if context.mode == MODE_BACKTEST:
        context.logger.info("回测配置：")
        context.logger.info("backtest_start_time = " + str(context.backtest_start_time))
        context.logger.info("backtest_end_time = " + str(context.backtest_end_time))
    else:
        context.logger.info("\n\n")
        context.logger.info("=" * 88)
        context.logger.info("实盘开始 ...")

    for symbol in symbols_map.keys():
        Trader = traders[symbols_map[symbol]["trader"]]
        kg = get_init_kg(context, symbol, generator=KlineGeneratorBy1Min, freqs=Trader.freqs, max_count=500)
        trader = Trader(kg, bi_mode="new", max_count=300)
        symbols_map[symbol]['trader'] = trader
        context.logger.info("{} 初始化完成，当前时间：{}".format(symbol, trader.end_dt))

    context.logger.info(f"交易配置：{symbols_map}")
    context.symbols_map = symbols_map

def on_bar(context, bars):
    context.unfinished_orders = get_unfinished_orders()

    for bar in bars:
        symbol = bar['symbol']
        try:
            adjust_position(context, symbol)
        except:
            traceback.print_exc()

    if context.now.minute == 58 and context.now.hour == 14 and context.mode == MODE_BACKTEST:
        report_account_status(context)


if __name__ == '__main__':
    # run(strategy_id='3d7bd7d2-2733-11eb-a40d-3cf0110437a2',
    #     mode=MODE_LIVE,
    #     filename='run_gm_1min.py',
    #     token='15bd09a572bff415a52b60001504f0a2dc38fa6e')

    run(filename='run_gm_1min.py',
        token='15bd09a572bff415a52b60001504f0a2dc38fa6e',
        strategy_id='add4163e-1825-11eb-a4e8-3cf0110437a2',
        mode=MODE_BACKTEST,
        backtest_start_time='2020-09-01 08:30:00',
        backtest_end_time='2020-10-15 15:30:00',
        backtest_initial_cash=100000000,
        backtest_transaction_ratio=1,
        backtest_commission_ratio=0.001,
        backtest_slippage_ratio=0,
        backtest_adjust=ADJUST_PREV,
        backtest_check_cache=1)

