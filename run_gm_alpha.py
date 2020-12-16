# coding: utf-8
"""执行股票 Alpha 策略"""
from pprint import pprint
import json
from src.gm_utils import *
from src.trader import traders
from src import conf


def calculate_long_score(context, symbol):
    """计算每只股票的多头表现得分"""
    if context.now.hour == 10 and context.now.minute == 0:
        bars = context.data(symbol=symbol, frequency='60s', count=300, fields='symbol,eob,open,close,high,low,volume')
        bars = format_kline(bars)
        bars = bars.to_dict("records")
        trader = context.symbols_map[symbol]['trader']
        bars_new = [x for x in bars if x['dt'] > trader.kg.end_dt]
        if bars_new:
            trader.update_kg(bars_new)
            trader.update_signals()
            score = trader.long_score()
            context.symbols_map[symbol]['trader'] = trader

            file_s = os.path.join(context.cache_path, "{}_signals.txt".format(symbol))
            with open(file_s, 'a', encoding="utf-8") as f:
                row = dict(trader.s)
                row['dt'] = row['dt'].strftime("%Y-%m-%d %H:%M:%S")
                f.write(str(row) + "\n")

            return score
    return -1

def adjust_positions(context, scores: dict):
    """批量调整股票持仓

    :param context:
    :param scores: 股票多头表现打分结果
    :return:
    """
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.future_id)

    file_scores = os.path.join(context.cache_path, "{}_scores.json".format(context.now.strftime("%Y%m%d")))
    json.dump(scores, open(file_scores, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    nav = account.cash.nav * 0.998
    scores_sum = sum(scores.values())

    # 方案一：加权分仓
    positions = {k: int(nav * v / scores_sum) for k, v in scores.items()}

    # # 方案二：TOP10均分
    # th = sorted(scores.values())[-10]
    # positions = {k: int(nav * 0.1) for k, v in scores.items() if v >= th}

    context.logger.info("{} - positions: {}".format(context.now, positions))
    pprint(positions)

    for symbol, pos in positions.items():
        order_target_value(symbol=symbol, value=pos, position_side=PositionSide_Long,
                           order_type=OrderType_Market, account=account.id)


def init(context):
    if context.mode == MODE_BACKTEST:
        data_path = "logs/alpha_{}".format(datetime.now().strftime("%Y%m%d%H%M%S"))
        context.wx_key = "2daec96b-f3f1-4f83-818b-2952fe2731c0"
    else:
        data_path = "logs/alpha_trader"
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

    # 设置需要跟踪的指数
    symbols = get_index_shares("创业板指数", "2020-01-01 09:30:00")
    subscribe(",".join(symbols), frequency='60s', count=300, wait_group=True, wait_group_timeout="300s")
    print(context.symbols)

    if context.mode == MODE_BACKTEST:
        context.logger.info("回测配置：")
        context.logger.info("backtest_start_time = " + str(context.backtest_start_time))
        context.logger.info("backtest_end_time = " + str(context.backtest_end_time))
    else:
        context.logger.info("\n\n")
        context.logger.info("=" * 88)
        context.logger.info("实盘开始 ...")

    symbols_map = {k: dict() for k in symbols}
    Trader = traders['ShareTraderV2a']
    for symbol in symbols:
        kg = get_init_kg(context, symbol, generator=KlineGeneratorBy1Min, freqs=Trader.freqs, max_count=500)
        trader = Trader(kg, bi_mode="new", max_count=500)
        symbols_map[symbol]['trader'] = trader
        context.logger.info("{} 初始化完成，当前时间：{}".format(symbol, trader.end_dt))

    context.logger.info(f"交易配置：{symbols}")
    context.symbols_map = symbols_map

def on_bar(context, bars):
    scores = {}
    for bar in bars:
        symbol = bar['symbol']
        try:
            score = calculate_long_score(context, symbol)
            scores[symbol] = score
        except:
            traceback.print_exc()

    if sum(scores.values()) > 0:
        adjust_positions(context, scores)

    if context.now.minute == 58 and context.now.hour == 14 and context.mode == MODE_BACKTEST:
        report_account_status(context)


if __name__ == '__main__':
    # run(strategy_id='3d7bd7d2-2733-11eb-a40d-3cf0110437a2',
    #     mode=MODE_LIVE,
    #     filename='run_gm_alpha.py',
    #     token='15bd09a572bff415a52b60001504f0a2dc38fa6e')

    run(filename='run_gm_alpha.py',
        token='15bd09a572bff415a52b60001504f0a2dc38fa6e',
        strategy_id='4751357e-385f-11eb-8a07-3cf0110437a2',
        mode=MODE_BACKTEST,
        backtest_start_time='2020-08-01 08:30:00',
        backtest_end_time='2020-11-30 15:30:00',
        backtest_initial_cash=100000000,
        backtest_transaction_ratio=1,
        backtest_commission_ratio=0.001,
        backtest_slippage_ratio=0,
        backtest_adjust=ADJUST_PREV,
        backtest_check_cache=1)

