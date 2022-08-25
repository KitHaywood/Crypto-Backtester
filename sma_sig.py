from time import time
from utils import *
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import pandas as pd
from datetime import datetime,timedelta
import argparse
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.graph_objs.scatter import Line
import json
import warnings
warnings.filterwarnings("ignore")

def prices(c,start,end):
    if c=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_BTC2" 
        WHERE datetimes>='{start}' 
        AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT * from "test_price_{c}" 
        WHERE datetimes>='{start}' 
        AND datetimes<='{end}' ORDER BY datetimes DESC;
        """)
    prices = pd.DataFrame.from_dict(res.mappings().all())
    prices = prices.set_index('datetimes',drop=False).sort_index(ascending=True)[start:end]
    pricedata = prices.rename(columns={
    "low":"Low",
    "high":"High",
    "close":"Close",
    "open":"Open",
    "datetimes":"datetime"
    }).set_index("datetime")
    return pricedata

def all_indics(c,start,end):
    if c=='BTC':
        res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop"
        FROM "acc_grad_test_btc_3" 
        WHERE "stop">='{start}' 
        AND "stop"<='{end}' 
        ORDER BY "stop" DESC; 
        """)
    else:
        res = con.execute(f"""
        SELECT DISTINCT accs[1],grads[1],mdates[1],win,deg,start,"stop" 
        FROM "test_accgrad_{c}" 
        WHERE "stop">='{start}' 
        AND "stop"<='{end}' 
        ORDER BY "stop" DESC; 
        """)  
    df = pd.DataFrame.from_dict(res.mappings().all())
    df = df.astype({
        'accs':float,
        'grads':float,
        'win':int,
        'deg':int})
    indics = {}
    wins = list(set(list(df['win'])))
    degs = list(set(list(df['deg'])))
    combs = [(x,y) for x in wins for y in degs]

    for w in wins:
        indics[w] = {}
        for d in degs:
            indics[w][d] = None

    for x,y in combs:
        hold  = df[(df['win']==x) & (df['deg']==y)].set_index('stop',drop=False).sort_index(ascending=True)
        indics[x][y] = hold.drop_duplicates(subset=['start','stop','win','deg'])
    return indics,wins,degs

def indicator(values):
    return values

def opstrat(p,ind,bstart,bend,btd,eq,wins,degs,mt,pracc):
    p = p[bstart:bend] # trim prices to relevant scope
    nind = {}
    for k,v in ind.items():
        nind[k] = {}
        for x,y in v.items():
            nind[k][x] = y[bstart:bend] # trim inds to relevant scope
            
    class FourierTimStandard(Strategy):
        """
        Strategy Class - Value of Derivatives 1 & 2 vs 0

        Optimal Strat Shape - [w , d]        
        """
        allindics = nind
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
            p,
            FourierTimStandard,
            cash=eq,
            commission=0.002
            )
    
    def maximiser(series):
        """takes series result of bt and returns a 
        float which maximises return and minimises num of trades"""
        return series['Equity Final [$]'] if 0 <= series['# Trades'] <= mt else 0
    
    btr = {}
    btr['bt_std'] = bt_std.optimize(
            wind1=wins,
            deg1=degs,
            wind2=wins,
            deg2=degs,
            maximize=maximiser,
            method="grid",
            max_tries=5000,
            constraint=lambda param: param
        )
    opst = {
        "win1":btr['bt_std']._strategy.wind1,
        "deg1":btr['bt_std']._strategy.deg1,
        "win2":btr['bt_std']._strategy.wind2,
        "deg2":btr['bt_std']._strategy.deg2
    }
    return opst

def add_metrics(_f): 
    _f['1_eq_ch'] = _f['equity'].pct_change() # pct ch with t-1
    # _f['long_ch'] = _f['equity'].pct_change(periods=5) #pct diff with t-5
    _f['rolling_max'] = [max(_f['equity'].loc[:i]) for i in list(_f.index)]
    _f['rolling_min'] = [min(_f['equity'].loc[:i]) for i in list(_f.index)]
    
    # Here need plan for overall 'equity-ness' of the model
    _f['mean_eq'] = [_f['equity'].loc[:i].mean() for i in list(_f.index)]
    _f['sma_eq'] = [_f['equity'].loc[:i].rolling(20).mean()[-1] for i in list(_f.index)]
    _f['ema_eq'] = [_f['equity'].loc[:i].ewm(span=15,adjust=False).mean()[-1] for i in list(_f.index)]
    return _f

def populate_columns(p,opst,eq,start,end,ind,pracc):
    p = p[start:end]
    w1 = opst['win1']
    w2 = opst['win2']
    d1 = opst['deg1']
    d2 = opst['deg2']
    s_ind1 = ind[w1][d2] # indicator df at w & d
    s_ind2 = ind[w1][d2] # indicator df at w & d
    data = p.copy()
    data['win1'] = [w1 for _ in range(p.shape[0])]
    data['win2'] = [w2 for _ in range(p.shape[0])]
    data['deg1'] = [d1 for _ in range(p.shape[0])]
    data['deg2'] = [d2 for _ in range(p.shape[0])]
    data['accs'] = s_ind1.accs
    data['grads'] = s_ind2.grads

    data['presignal'] = [0 if x==0 else 1 if ((data.iloc[x-1]['grads'] < data.iloc[x-1]['accs']) and (data.iloc[x]['grads'] > data.iloc[x]['accs']))
                         else -1 if ((data.iloc[x-1]['grads'] > data.iloc[x-1]['accs']) and (data.iloc[x]['grads'] < data.iloc[x]['accs']))
                         else 0 for x in range(data.shape[0])]        
    posdf = data[data['presignal']!=0]
    data['signal'] = data['presignal'].replace(to_replace=0,method="ffill")
    data['equity'] =  [None for _ in range(p.shape[0])]
    data['pct_ch'] = data['Close'].pct_change()
    
    _f = pd.DataFrame().reindex_like(data)
    
    for i,x in data.iterrows():
        if i == min(data.index):
            x['equity'] = eq
            _f.loc[i] = x
        else:
            lasteq = _f.loc[i-timedelta(hours=1)]['equity']
            if x['signal']==0:
                cureq = lasteq
            elif x['signal']==1:
                cureq = lasteq * (1 + x['pct_ch'])
            elif x['signal']==-1:
                cureq = lasteq * (1 + (x['pct_ch']*-1.0))
            x['equity'] = cureq
            try:
                _f.loc[i] = x
            except ValueError as e:
                print(e)
                
    _f = add_metrics(_f)
    _f['hwm'] = [max(_f['equity'].loc[:i]) for i in list(_f.index)]
    return _f,posdf
    
def indix_main(c,md,btd,mt,pracc,mdd,ind):
    M_end = datetime.today().replace(minute=0,second=0,microsecond=0)
    M_start = M_end - timedelta(hours=md+btd)
    eq = 100000
    

    p = prices(c,M_start,M_end) # (1) Load Prices - here p is [btd+md]
    ws = list(range(100,1600,100)) # (2) inds required for (2)
    ds = list(range(4,17))
    
    # Sort starts and ends properly here
    istart = M_start
    iend = M_start+timedelta(hours=btd) # check
    opst = opstrat(
        p, # prices df
        ind, # dict of dict of indicator dfs
        istart, # the initial backtest datetimes start
        iend, # the end of the initial backtest
        btd, # the depth of the in sample backtests in hours
        eq, # the equity as int
        ws, # windows
        ds, # degrees
        mt, # max trades
        pracc # preceding acceleration depth
        ) 
    
    # M_end is major end, iend is the end of the initial backtest
    bigpos = pd.DataFrame()
    data,posdf = populate_columns(p,opst,eq,iend,M_end,ind,pracc)
    bigpos = pd.concat([bigpos,posdf])
    f = pd.DataFrame().reindex_like(data)
    i = min(f.index)
    outstrat = {}
    outstrat[iend] = opst
    maxeq = 0
    total_area = 0
        
    while i != max(f.index): 

        total_area = total_area + (data.loc[i]['mean_eq'] - data.loc[i]['equity'])

        print(maxeq,total_area,data.loc[i]['equity'])
        
        if maxeq==data.loc[i]['rolling_min']==data.loc[i]['equity']:
            f.loc[i] = data.loc[i]
        if total_area > mdd :

            opst = opstrat(p,ind,i-timedelta(hours=btd),i,btd,data.loc[i]['equity'],ws,ds,mt,pracc)
            outstrat[i] = opst
            data,posdf = populate_columns(
                p,
                opst,
                data.loc[i]['equity'],
                i,
                M_end,
                ind,
                pracc
                )
        
            bigpos = pd.concat([bigpos,posdf])
            f.loc[i:] = data.loc[i:]
            total_area = 0 # reset area to 0
            maxeq = 0

        else:
            f.loc[i] = data.loc[i]
            
        i = i+timedelta(hours=1)
        
    f = add_metrics(f)
    bigpos['colour'] = ['gold' if x==1 else 'grey' if x==-1 else None for x in list(bigpos.presignal)]
    bigpos['symbol'] = ['triangle-up' if x==1 else 'triangle-down' if x==-1 else None for x in list(bigpos.presignal)]
    return f,opst,outstrat,bigpos


if __name__=="__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--out',
        type=str,
        required=False,
        help='choose either plotly/csv/json'
    )
    parser.add_argument(
        '--crypto',
        type=str,
        required=False,
        help='choose either XLM/REP/BTC'
    )
    parser.add_argument(
        '--depth',
        type=int,
        required=False,
        help='choose int in hours'
    )
    parser.add_argument(
        '--bt_depth',
        type=int,
        required=False,
        help='choose int in hours'
    )
    parser.add_argument(
        '--max_drawdowndepth',
        type=float,
        required=False,
        help='between 0.0 - 1.0'
    )
    args = parser.parse_args()
    
    if args.depth:
        pass
    else:
        args.depth = 1000
    
    if args.crypto:
        pass
    else:
        args.crypto = "BTC"
            
    if args.bt_depth:
        pass
    else:
        args.bt_depth=200
    
    if args.max_drawdowndepth:
        pass
    else:
        args.max_drawdowndepth = 250000
    # print(args)
    global max_trades,btd,md,mdd
    pracc = 0
    max_trades = 10
    c = args.crypto
    btd = args.bt_depth # backtest depth
    md = args.depth # backtest depth
    mdd = args.max_drawdowndepth
    # c,md,btd,mt,pracc,mdd
    data,opst,outstrat,posdf = indix_main(
        c=c,
        md=md, # model depth (what is plotted)
        btd=btd, # backtest depth,
        mt=max_trades,
        pracc=pracc,
        mdd=mdd
    )

    # class PdEncoder(json.JSONEncoder):
    #     def default(self, obj):
    #         if isinstance(obj, pd.Timestamp):
    #             return str(obj)
    #         return json.JSONEncoder.default(self, obj)
    
    # csvpath = os.path.join(os.getcwd(),f'output_{c}_{datetime.today().replace(minute=0,second=0,microsecond=0).isoformat(sep="T")}.csv')
    # jsonpath = os.path.join(os.getcwd(),f'output{c}_{datetime.today().replace(minute=0,second=0,microsecond=0).isoformat(sep="T")}.json')
    # if args.out=='json':
    #     with open(jsonpath,'w') as f_out:
    #         json.dump(data.to_dict(orient='records'),f_out,cls=PdEncoder)
    # elif args.out=='csv':
    #     data.to_csv(csvpath)
    # elif args.out=='plotly':
    #     fig = plot(c,data,opst,outstrat,posdf)
    breakpoint()