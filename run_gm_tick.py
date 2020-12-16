# coding: utf-8
from pprint import pprint
from src.gm_utils import *
from src.trader import traders
from src import conf


def adjust_position(context, symbol):
    ticks = context.data(symbol=symbol, frequency='tick', count=300)
    trader = context.symbols_map[symbol]['trader']
    ticks_new = [format_tick(x) for x in ticks if x['created_at'] > trader.kg.end_dt and x['price'] > 0]
    if ticks_new:
        trader.update_kg(ticks_new)
        trader.update_signals()
    context.symbols_map[symbol]['trader'] = trader
    context.desc = str(context.symbols_map)

    last_tick = ticks[-1]
    if context.mode == MODE_BACKTEST:
        if last_tick["created_at"].minute % 30 == 0 and last_tick["created_at"].second < 1:
            pprint(trader.s)
            print("\n")
    else:
        if last_tick["created_at"].minute % 5 == 0 and last_tick["created_at"].second < 1:
            pprint(trader.s)
            print("\n")

    exchange = symbol.split(".")[0]
    if exchange in ["SZSE", "SHSE"]:
        adjust_share_position(context, symbol, trader)
    else:
        adjust_future_position(context, symbol, trader)

def init(context):
    if context.mode == MODE_BACKTEST:
        data_path = "logs/tick_{}".format(datetime.now().strftime("%Y%m%d%H%M%S"))
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
        kg = get_init_kg(context, symbol, generator=KlineGeneratorByTick, freqs=Trader.freqs)
        trader = Trader(kg, bi_mode="new")
        symbols_map[symbol]["trader"] = trader
        context.logger.info("{} 初始化完成，当前时间：{}".format(symbol, trader.end_dt))

    context.logger.info(f"交易配置：{symbols_map}")
    context.symbols_map = symbols_map
    subscribe(",".join(context.symbols_map.keys()), frequency='tick', wait_group=False, wait_group_timeout='30s')


def on_tick(context, tick):
    symbol = tick['symbol']
    context.unfinished_orders = get_unfinished_orders()
    try:
        adjust_position(context, symbol)
    except:
        traceback.print_exc()


if __name__ == '__main__':
    # run(strategy_id='3d7bd7d2-2733-11eb-a40d-3cf0110437a2',
    #     mode=MODE_LIVE,
    #     filename='run_gm_tick.py',
    #     token='15bd09a572bff415a52b60001504f0a2dc38fa6e')

    run(filename='run_gm_tick.py',
        token='15bd09a572bff415a52b60001504f0a2dc38fa6e',
        strategy_id='13a442e7-2962-11eb-8a24-3cf0110437a2',
        mode=MODE_BACKTEST,
        backtest_start_time='2020-10-01 08:30:00',
        backtest_end_time='2020-11-20 15:00:00',
        backtest_initial_cash=30000000,
        backtest_transaction_ratio=1,
        backtest_commission_ratio=0.001,
        backtest_slippage_ratio=0,
        backtest_adjust=ADJUST_PREV,
        backtest_check_cache=1)

