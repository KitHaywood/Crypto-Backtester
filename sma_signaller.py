#!/usr/bin/python3
from utils import *
from update_prices import _UP_get_latest_price
from update_coefs import _UC_get_latest_coef
from update_accgrad import _AG_get_latest_acc_grad
from api import make_client, setenv
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
from update_prices import _UP_get_latest_price
from sqlalchemy import Table,MetaData,Column,String, Integer, Float,DateTime,ARRAY,NUMERIC,TEXT
import sys
import json

def parse_read_result(res,allindics):
    #  res is as (win,deg,start,stop,o,df)
    for w,d,start,stop,df in res:
        allindics[f"{start}:{stop}"][w][d] = df
    return allindics

def make_read_args(agtbl,intervals):
    """
    Makes list of tuples of (C,W,D,Start,Stop,offset)
    """
    res = []
    for w in wins:
        for d in degs:
            for start,stop in intervals:
                res.append((agtbl,w,d,start,stop))
    return res

def prep_allindics(allindics,intervals):
    """
    Makes the empty dictionary for population
    """
    for start,stop in intervals:
        allindics[f"{start}:{stop}"] = {}
        for w in wins:
            allindics[f"{start}:{stop}"][w] = {}
            for d in degs:
                allindics[f"{start}:{stop}"][w][d] = None
    return allindics

def S_get_price_data(pricetbl,start,stop):
    res = con.execute(f"""
        SELECT * FROM "{pricetbl}" 
        WHERE datetimes>='{start}' 
        AND datetimes<='{stop}';
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def check_tbl_exist(postbl,sigtbl,sltbl):
    res = con.execute(f"""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public' AND table_type='BASE TABLE';
    """)
    xx = pd.DataFrame.from_dict(res.mappings().all())
    tbls = [x for x in xx.table_name]
    pos_exists = bool([x for x in tbls if postbl in x])
    sig_exists = bool([x for x in tbls if sigtbl in x])
    sl_exists = bool([x for x in tbls if sltbl in x])
    return {
        "position":pos_exists,
        "signal":sig_exists,
        "SL":sl_exists,
    }

def create_sigtbl(exists,sigtbl):
    sig_exists = exists['signal']
    if sig_exists:
        return 0
    else:
        res = con.execute(f"""
        CREATE TABLE IF NOT EXISTS {sigtbl} (
            record_write_time TIMESTAMP NOT NULL,
            interval_start TIMESTAMP NOT NULL,
            interval_end TIMESTAMP NOT NULL,
            curr_pos_size NUMERIC,
            curr_pos_dir INT,
            signal INT, 
            wind1 INT,
            deg1 INT,
            wind2 INT,
            deg2 INT
        );
        """)
        return 0

def create_postbl(exists,postbl):
    pos_exists = exists['position']
    if pos_exists:
        return 0
    else:
        res = con.execute(f"""
        CREATE TABLE IF NOT EXISTS {postbl} (
            interval_start TIMESTAMP NOT NULL,
            interval_end TIMESTAMP NOT NULL,
            position_size NUMERIC,
            direction INT,
            account_id TEXT,
            pct_equity_change NUMERIC,
            equity_change NUMERIC,
            entry_time TIMESTAMP,
            entry_price NUMERIC,
            current_price NUMERIC
        );
        """)
        return 0


def create_sltbl(exists,sltbl):
    sl_exists = exists['SL']
    if sl_exists:
        return 0
    else:
        res = con.execute(f"""
        CREATE TABLE IF NOT EXISTS {sltbl} (
            interval_start TIMESTAMP NOT NULL,
            interval_end TIMESTAMP NOT NULL,
            entry_price NUMERIC,
            sl_price NUMERIC,
            current_price NUMERIC,
            direction INT
        );
        """)
        return 0


def get_curr_exch_equity():
    setenv()
    client = make_client()
    acnts = client.get_accounts()
    return pd.DataFrame(acnts)

def get_postbl_equity(postbl):
    """
    Returns Scalar
    """
    return None

def get_latest_position(postbl):
    res = con.execute(f"""
    SELECT * FROM {postbl} ORDER BY interval_end DESC LIMIT 1
    """)
    return pd.DataFrame.from_dict(res.mappings().all())

def get_latest_signal(sigtbl):
    res = con.execute(f"""
    SELECT * FROM {sigtbl} ORDER BY interval_end DESC LIMIT 1
    """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_latest_price(pricetbl):
    res = con.execute(f"""
        SELECT * FROM "{pricetbl}" 
        WHERE datetimes=(SELECT MAX(datetimes) FROM "{pricetbl}");
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_latest_coef(ctbl,opstrat):
    res = con.execute(f"""
        SELECT * FROM "{ctbl}" 
        WHERE "end"=(SELECT MAX("end") FROM "{ctbl}")
        AND "window"={opstrat['win']}
        AND deg={opstrat['deg']} ORDER BY "end" DESC; 
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_latest_ag(agtbl,opstrat):
    res = con.execute(f"""
        SELECT * FROM "{agtbl}" 
        WHERE "stop"=(SELECT MAX("stop") FROM "{agtbl}") 
        AND "win"={opstrat['win1']} 
        AND "deg"={opstrat['deg1']} ORDER BY "stop" DESC;
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_l5ag(agtbl,opstrat):
    res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" 
        FROM "{agtbl}" 
        WHERE "stop">=
        (SELECT MIN("stop") as "minstop" 
        FROM (SELECT DISTINCT "stop" FROM "{agtbl}" 
            ORDER BY "stop" DESC LIMIT 5)
        AS "foo") 
        AND "win"={opstrat['win1']} 
        AND deg={opstrat['deg1']} ORDER BY "stop" DESC;
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_l5g(agtbl,opstrat):
    res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" 
        FROM "{agtbl}" 
        WHERE "stop">=
        (SELECT MIN("stop") as "minstop" 
        FROM (SELECT DISTINCT "stop" FROM "{agtbl}" 
            ORDER BY "stop" DESC LIMIT 5)
        AS "foo") 
        AND "win"={opstrat['win1']} 
        AND deg={opstrat['deg1']} ORDER BY "stop" DESC;
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def S_get_l5a(agtbl,opstrat):
    res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" 
        FROM "{agtbl}" 
        WHERE "stop">=
        (SELECT MIN("stop") as "minstop" 
        FROM (SELECT DISTINCT "stop" FROM "{agtbl}" 
            ORDER BY "stop" DESC LIMIT 5)
        AS "foo") 
        AND "win"={opstrat['win2']} 
        AND deg={opstrat['deg2']} ORDER BY "stop" DESC;
        """)
    return pd.DataFrame.from_dict(res.mappings().all())

def indicator(values):
    return values

def get_opter_strat(pricetbl,agtbl,postbl,sigtbl,sltbl):
    """
    This should check for existence, retreive if possible else calculate
    """
    exists = check_tbl_exist(postbl,sigtbl,sltbl)
    global offsets,degs,wins 
    offsets = [int(x) for x in range(1,10,1)]
    degs = [int(x) for x in range(4,17)] # sort this to select uniques from db
    wins = [int(x) for x in range(100,1600,100)]
    global allindics
    allindics = {}

    isempty = {}
    tbls = [postbl,sigtbl,sltbl]
    for t in tbls:
        emptyres = con.execute(f"""
        SELECT * FROM {t};  
        """)
        isempty[t] = pd.DataFrame.from_dict(emptyres.mappings().all()).empty
    # pdb.set_trace()
    if exists['signal'] and not isempty[sigtbl]:
        print("if exists['signal'] and not isempty[sigtbl]:")
        l_sig = get_latest_signal(sigtbl)
        if l_sig.empty:
            print("216 if l_sig.empty:")
            l_price = _UP_get_latest_price(pricetbl)
            prestart = l_price-timedelta(hours=200)
            preend = l_price
            prices = S_get_price_data(pricetbl,prestart,preend) # CANDLESTICK DATA
            pricedata = prices.rename(columns={
            "low":"Low",
            "high":"High",
            "close":"Close",
            "open":"Open",
            "datetimes":"datetime"
            }).set_index("datetime")
            intervals = [(prestart,preend)]
            allindics = prep_allindics(allindics,intervals) 
            args = make_read_args(agtbl,intervals)
            debugres = []
            for arg in args:
                debugres.append(create_df(*arg))
            allindics = parse_read_result(debugres,allindics)
            print("247 before first class")
            class FourierTimStandard(Strategy):

                allindics = allindics[f"{str(prestart)}:{str(preend)}"]
                wind1 = 800
                deg1 = 4
                wind2 = 200
                deg2 = 12

                def init(self):
                    self.grad = self.I(
                        indicator, 
                        self.allindics[self.wind1][self.deg1].grads
                        )
                    self.acc = self.I(
                        indicator,
                        self.allindics[self.wind2][self.deg2].accs
                        )

                def next(self):
                    if crossover(self.grad,self.acc):
                        self.position.close()
                        self.buy()

                    elif crossover(self.acc, self.grad): 
                        self.position.close()
                        self.sell()
            bt_std = Backtest(
                    pricedata[['Open','Close','High','Low']][prestart:preend],
                    FourierTimStandard,
                    cash=1_000_000,
                    commission=0.002
                    )
            btresult = {}
            btresult['bt_std'] = bt_std.optimize(
                    wind1=range(100,1600,100),
                    deg1=range(4,17,1),
                    wind2=range(100,1600,100),
                    deg2=range(4,17,1),
                    maximize='Equity Final [$]',
                    method="grid"
                )
            opstrat = {
                "win1":btresult['bt_std']._strategy.wind1,
                "win2":btresult['bt_std']._strategy.wind2,
                "deg1":btresult['bt_std']._strategy.deg1,
                "deg2":btresult['bt_std']._strategy.deg2
            }
            # pdb.set_trace()
            return opstrat 
        else:
            print("l_sig is empty")
            pdb.set_trace()
            opstrat = {
                "win1":l_sig['wind1'].values[0],
                "win2":l_sig['wind2'].values[0],
                "deg1":l_sig['deg1'].values[0],
                "deg2":l_sig['deg2'].values[0]
            }
            l5_ag = S_get_l5ag(agtbl,opstrat)
            newgrads = list(l5_ag['grads'])
            newaccs = list(l5_ag['accs'])
            depth = 59
            newres = con.execute(f"""
            SELECT * FROM {sigtbl} ORDER BY "interval_end" DESC LIMIT {depth+1};
            """)
            badpos = pd.DataFrame.from_dict(newres.mappings().all())
            pdb.set_trace()
            if (badpos.shape[0] > depth and len(list(set(list(badpos['deg1']))))==1 
                and len(list(set(list(badpos['wind1']))))==1 and len(list(set(list(badpos['deg2']))))==1 
                and len(list(set(list(badpos['wind2']))))==1and all(badpos['curr_pos_size']==0)):
                nohit = True
            else:
                nohit=False

            if nohit==True:

                l_price = _UP_get_latest_price(pricetbl)
                prestart = l_price-timedelta(hours=200)
                preend = l_price
                prices = S_get_price_data(pricetbl,prestart,preend) # CANDLESTICK DATA
                pricedata = prices.rename(columns={
                "low":"Low",
                "high":"High",
                "close":"Close",
                "open":"Open",
                "datetimes":"datetime"
                }).set_index("datetime")
                intervals = [(prestart,preend)]
                allindics = {}
                allindics = prep_allindics(allindics,intervals) 
                args = make_read_args(agtbl,intervals)
                debugres = []

                for arg in args:
                    debugres.append(create_df(*arg))
                allindics = parse_read_result(debugres,allindics)

                class FourierTimStandard(Strategy):
                    allindics = allindics[f"{str(prestart)}:{str(preend)}"]
                    wind1 = 800
                    deg1 = 4
                    wind2 = 200
                    deg2 = 12

                    def init(self):
                        self.grad = self.I(
                            indicator, 
                            self.allindics[self.wind1][self.deg1].grads
                            )
                        self.acc = self.I(
                            indicator,
                            self.allindics[self.wind2][self.deg2].accs
                            )

                    def next(self):
                        if crossover(self.grad,self.acc):
                            self.position.close()
                            self.buy()

                        elif crossover(self.acc, self.grad): 
                            self.position.close()
                            self.sell()
                
                bt_std = Backtest(
                        pricedata[['Open','Close','High','Low']][prestart:preend],
                        FourierTimStandard,
                        cash=1_000_000,
                        commission=0.002
                        )
                btresult = {}
                btresult['bt_std'] = bt_std.optimize(
                        wind1=range(100,1600,100),
                        deg1=range(4,17,1),
                        wind2=range(100,1600,100),
                        deg2=range(4,17,1),
                        maximize='Equity Final [$]',
                        method="grid"
                    )
                opstrat = {
                    "win1":btresult['bt_std']._strategy.wind1,
                    "win2":btresult['bt_std']._strategy.wind2,
                    "deg1":btresult['bt_std']._strategy.deg1,
                    "deg2":btresult['bt_std']._strategy.deg2
                }
                # pdb.set_trace()
                return opstrat
            else:
                return opstrat

    elif exists['signal'] and isempty[sigtbl]:
        
        print("elif exists['signal'] and isempty[sigtbl]:")
        l_price = _UP_get_latest_price(pricetbl)
        prestart = l_price-timedelta(hours=200)
        preend = l_price

        prices = S_get_price_data(pricetbl,prestart,preend) # CANDLESTICK DATA
        pricedata = prices.rename(columns={
        "low":"Low",
        "high":"High",
        "close":"Close",
        "open":"Open",
        "datetimes":"datetime"
        }).set_index("datetime")

        intervals = [(prestart,preend)]
        allindics = prep_allindics(allindics,intervals) 
        args = make_read_args(agtbl,intervals)
        debugres = []
        for arg in args:
            debugres.append(create_df(*arg))

        allindics = parse_read_result(debugres,allindics)
        class FourierTimStandard(Strategy):

            allindics = allindics[f"{str(prestart)}:{str(preend)}"]
            wind1 = 800
            deg1 = 4
            wind2 = 200
            deg2 = 12

            def init(self):
                self.grad = self.I(
                    indicator, 
                    self.allindics[self.wind1][self.deg1].grads
                    )
                self.acc = self.I(
                    indicator,
                    self.allindics[self.wind2][self.deg2].accs
                    ) 

            def next(self):
                if crossover(self.grad,self.acc): 
                    self.position.close()
                    self.buy()

                elif crossover(self.acc, self.grad): 
                    self.position.close()
                    self.sell()
        
        bt_std = Backtest(
                pricedata[['Open','Close','High','Low']][prestart:preend],
                FourierTimStandard,
                cash=1_000_000,
                commission=0.002
                )
        btresult = {}
        btresult['bt_std'] = bt_std.optimize(
                wind1=range(100,1600,100),
                deg1=range(4,17,1),
                wind2=range(100,1600,100),
                deg2=range(4,17,1),
                maximize='Equity Final [$]',
                method="grid"
            )
        opstrat = {
            "win1":btresult['bt_std']._strategy.wind1,
            "win2":btresult['bt_std']._strategy.wind2,
            "deg1":btresult['bt_std']._strategy.deg1,
            "deg2":btresult['bt_std']._strategy.deg2
        }
        # pdb.set_trace()
        return opstrat
    else:
        create_sigtbl(exists,sigtbl) # make table
        return opstrat


def eval_signal(pricetbl,agtbl,opstrat):
    """
    Evaluates signal - using opstrat the new coefs, the new accgrads and the price
    return -1,0,+1
    """

    l5_a = S_get_l5a(agtbl,opstrat) # this is acc
    l5_g = S_get_l5g(agtbl,opstrat) # this is grad 

    if (l5_a.iloc[1]['accs'] > l5_g.iloc[1]['grads'] and l5_g.iloc[0]['grads'] > l5_a.iloc[0]['accs']):
        signal = 1  
    elif (l5_a.iloc[1]['accs'] < l5_g.iloc[1]['grads'] and l5_g.iloc[0]['grads'] < l5_a.iloc[0]['accs']):
        signal = -1
    else:
        signal = 0
    return signal


def eval_position(signal,postbl,sigtbl,sltbl):
    exist = check_tbl_exist(postbl,sigtbl,sltbl)
    lastpos = get_latest_position(postbl)
    if exist['position'] and lastpos.empty:
        curpos = get_latest_position(postbl)
        if curpos.empty:
            curpos = 0
    else:
        curpos = 0

    if (curpos == 1) and (signal == 0):
        pos = 0
    elif (curpos == -1) and (signal == 0):
        pos = 0
    elif (curpos == 0) and (signal == 1):
        pos = 1
    elif (curpos == 0) and (signal == -1):
        pos = -1
    elif (curpos == 0) and (signal == 0):
        pos = 0
    else:
        pass
    return pos


def execute_position(position):

    def construct_position_packet(position):
        return None
    """
    This actually hits the market with the order - the position should be json maybe? 
    """
    return None

def write_signal(signal,position,opstrat,pricetbl,sigtbl,postbl):
    """
    Write to db
    """
    l_price = S_get_latest_price(pricetbl)
    cur_pos = get_latest_position(postbl)
    win1 = opstrat['win1']
    win2 = opstrat['win2']
    deg1 = opstrat['deg1']
    deg2 = opstrat['deg2']
    if cur_pos.empty:
        cur_pos = pd.DataFrame({"position_size":0,"direction":0},index=[0])
    df = pd.DataFrame.from_dict(
        {
            "record_write_time":datetime.today().replace(second=0,microsecond=0),
            "interval_start":l_price['datetimes'],
            "interval_end":l_price['datetimes']+timedelta(hours=1),
            "curr_pos_size":int(cur_pos['position_size']),
            "curr_pos_dir":int(cur_pos['direction']),
            "signal":signal,
            "wind1":win1,
            "deg1":deg1,
            "wind2":win2,
            "deg2":deg2,
        }
    )

    dtypes = {
        "record_write_time":DateTime,
        "interval_start":DateTime,
        "interval_end":DateTime,
        "curr_pos_size":Integer,
        "curr_pos_dir":Integer,
        "signal":Integer,
        "wind1":Integer,
        "wind2":Integer,
        "deg1":Integer,
        "deg2":Integer
    }
    df.to_sql(sigtbl,con=db,if_exists="append",index=False,dtype=dtypes)
    return df

def write_position(position,signal,pricetbl,postbl):

    setenv() # CAREFUL HERE - specific portfolios
    client = make_client()
    l_price = S_get_latest_price(pricetbl)
    cur_price = l_price['close']
    accdf = pd.DataFrame(client.get_accounts())
    account_id = accdf[accdf['currency']=="BTC"]['id'].values[0]

    direction = signal # -1,0,+1
    if direction != 0:
        position_size = float(accdf[accdf['currency']=="USD"]['balance'].values[0])/cur_price # FOR THE MOMENT EXECUTE MAXIMUM POSITION SIZE
    else:
        position_size = 0
    if direction != 0:

        entry_price = l_price.close
        entry_time = datetime.today().replace(second=0,microsecond=0)

        if entry_time.replace(minute=0)==l_price.datetimes:
            pct_equity_change = None
            equity_change = None
        elif direction==1 and entry_time.replace(minute=0) != l_price.datetimes:
            equity_change = cur_price - entry_price
            pct_equity_change = (equity_change/entry_price)*100
        elif direction==-1 and entry_time.replace(minute=0) != l_price.datetimes:
            equity_change = entry_price - cur_price
            pct_equity_change = (equity_change/entry_price)*100
    
    else:

        entry_price = None
        entry_time = None
        equity_change = None
        pct_equity_change = None

    df = pd.DataFrame.from_dict(
        {
            "interval_start":l_price['datetimes'],
            "interval_end":l_price['datetimes']+timedelta(hours=1),
            "position_size":position_size,
            "direction":direction,
            "account_id":account_id,
            "pct_equity_change":pct_equity_change,
            "entry_price":entry_price,
            "entry_time":entry_time,
            "equity_change":equity_change,
            "current_price":l_price.close
        }
    )

    dtypes = {
        "interval_start":DateTime,
        "interval_end":DateTime,
        "position_size":NUMERIC,
        "direction":Integer,
        "account_id":TEXT,
        "pct_equity_change":NUMERIC,
        "entry_price":NUMERIC,
        "entry_time":DateTime,
        "equity_change":NUMERIC,
        "current_price":NUMERIC
    }
    df.to_sql(postbl,con=db,if_exists="append",index=False,dtype=dtypes)
    return df

def write_sl(signal,postbl,sltbl,pricetbl):

    full_pos = get_latest_position(postbl)
    l_price = S_get_latest_price(pricetbl)
    cur_price = l_price['close'].values[0]

    if any([full_pos.empty,(full_pos['position_size']==0).values[0]]):
        entry_price = None
        direction = None
        sl_price = None
    else:
        entry_price = float(full_pos['entry_price'].values[0])
        direction = int(full_pos['direction'].values[0])
        if direction == -1:
            if ((entry_price-cur_price)/entry_price)<0.01:
                sl_price = cur_price
            else:
                sl_price = cur_price*0.99
        elif direction == 1:
            if ((cur_price-entry_price)/entry_price)<0.01:
                sl_price = cur_price
            else:
                sl_price = cur_price*1.01
        else:
            pass
    
    df = pd.DataFrame.from_dict(
        {
            "interval_start":l_price['datetimes'],
            "interval_end":l_price['datetimes']+timedelta(hours=1),
            "entry_price":entry_price,
            "sl_price":sl_price,
            "current_price":cur_price,
            "direction":direction            
        }
    )

    dtypes = {
            "interval_start":DateTime,
            "interval_end":DateTime,
            "entry_price":NUMERIC,
            "sl_price":NUMERIC,
            "current_price":NUMERIC,
            "direction":Integer   
    }
    df.to_sql(sltbl,con=db,if_exists="append",index=False,dtype=dtypes)
    return df


def main(pricetbl="test_price_BTC2",
    ctbl="testing_coef_BTC5",
    agtbl="acc_grad_test_btc_3",
    postbl="test_pos_btc_2",
    sigtbl="test_sig_btc_2",
    sltbl="test_sl_btc_2"):
    # Target Table Naming and Control

    exists = check_tbl_exist(postbl,sigtbl,sltbl)

    # CREATE DUMMY TRACKNG TABLES
    create_postbl(exists,postbl)
    create_sigtbl(exists,sigtbl)
    create_sltbl(exists,sltbl)

    opstrat = get_opter_strat(pricetbl,agtbl,postbl,sigtbl,sltbl)
    signal = eval_signal(
            pricetbl,
            agtbl,
            opstrat)
    position = eval_position(signal,postbl,sigtbl,sltbl)
    # pdb.set_trace()
    wsig = write_signal(signal,position,opstrat,pricetbl,sigtbl,postbl)
    wpos = write_position(position,signal,pricetbl,postbl)
    wsl = write_sl(signal,postbl,sltbl,pricetbl)
    return 0


if __name__=="__main__":
    # opstrat resets after 59 hours if no hit
    if sys.argv[1]=="BTC":
        pricetbl="test_price_BTC2"
        ctbl="testing_coef_BTC5"
        agtbl="acc_grad_test_btc_3"
        crypto = sys.argv[1]
        postbl = str(f"sma_pos_{crypto}_1").lower()
        sigtbl = str(f"sma_sig_{crypto}_1").lower()
        sltbl = str(f"sma_sl_{crypto}_1").lower()
        main(
            pricetbl=pricetbl,
            ctbl=ctbl,
            agtbl=agtbl,
            postbl=postbl,
            sigtbl=sigtbl,
            sltbl=sltbl
        )
    else:
        crypto = sys.argv[1]
        pricetbl=f"test_price_{crypto}"
        ctbl=f"test_coef_{crypto}"
        agtbl=f"test_accgrad_{crypto}"
        postbl = str(f"sma_pos_{crypto}_1").lower()
        sigtbl = str(f"sma_sig_{crypto}_1").lower()
        sltbl = str(f"sma_sl_{crypto}_1").lower()
        main(
            pricetbl=pricetbl,
            ctbl=ctbl,
            agtbl=agtbl,
            postbl=postbl,
            sigtbl=sigtbl,
            sltbl=sltbl
        )
