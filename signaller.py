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
        wind = 800
        deg = 4

        def init(self):
            self.grad = self.I(
                    indicator, 
                    self.allindics[self.wind][self.deg].grads
                    )
            self.acc = self.I(
                indicator,
                self.allindics[self.wind][self.deg].accs
                ) 
            self.zeros = self.I(
                indicator,
                np.zeros(len(self.data.Close))
                )

        def next(self):
            if pracc==0:
                if (self.grad > 0) & all(self.acc > 0) & (self.grad[-2] < 0): 
                    self.position.close()
                    self.buy()

                elif (self.grad < 0) & all(self.acc < 0) & (self.acc[-2] > 0): 
                    self.position.close()
                    self.sell()
            else:
                if (self.grad > 0) & all(self.acc[-pracc:] > 0) & (self.grad[-2] < 0): 
                    self.position.close()
                    self.buy()

                elif (self.grad < 0) & all(self.acc[-pracc:] < 0) & (self.acc[-2] > 0): 
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
            wind=wins,
            deg=degs,
            maximize=maximiser,
            method="grid",
            constraint=lambda param: param
        )
    opst = {
        "win":btr['bt_std']._strategy.wind,
        "deg":btr['bt_std']._strategy.deg
    }
    return opst

def add_metrics(_f): 
    _f['1_eq_ch'] = _f['equity'].pct_change() # pct ch with t-1
    _f['long_ch'] = _f['equity'].pct_change(periods=5) #pct diff with t-5
    _f['rolling_max'] = [max(_f['equity'].loc[:i]) for i in list(_f.index)]
    _f['rolling_min'] = [min(_f['equity'].loc[:i]) for i in list(_f.index)]
    
    # Here need plan for overall 'equity-ness' of the model
    _f['mean_eq'] = [_f['equity'].loc[:i].mean() for i in list(_f.index)]
    _f['sma_eq'] = [_f['equity'].loc[:i].rolling(20).mean()[-1] for i in list(_f.index)]
    _f['ema_eq'] = [_f['equity'].loc[:i].ewm(span=15,adjust=False).mean()[-1] for i in list(_f.index)]
    return _f

def populate_columns(p,opst,eq,start,end,ind,pracc):
    p = p[start:end]
    w = opst['win']
    d = opst['deg']
    s_ind = ind[w][d] # indicator df at w & d
    data = p.copy()
    data['win'] = [w for _ in range(p.shape[0])]
    data['deg'] = [d for _ in range(p.shape[0])]
    data['accs'] = s_ind.grads
    data['grads'] = s_ind.accs

    if pracc==0:
        data['presignal'] = [0 if x==0 else 1 if (data.iloc[x]['accs']>0 and data.iloc[x-1]['grads']<0 and data.iloc[x]['grads']>0)
                        else -1 if (data.iloc[x]['accs']<0 and data.iloc[x-1]['grads']>0 and data.iloc[x]['grads']<0)
                        else 0 for x in range(data.shape[0])]
    else:
        data['presignal'] = [0 if x==0 else 1 if (all(data.iloc[x-pracc:]['accs']>0) and data.iloc[x-1]['grads']<0 and data.iloc[x]['grads']>0)
                        else -1 if (all(data.iloc[x-pracc:]['accs']<0) and data.iloc[x-1]['grads']>0 and data.iloc[x]['grads']<0)
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
    # breakpoint()
    return _f,posdf
    

def plot(c,data,opst,outstrat,posdf):

    pricetc = go.Scatter(x=data.index,y=data['Close'],line = Line({'color': 'rgb(0, 0, 128)', 'width': 1}),name='Price')
    # sigtc = px.Scatter(posdf,x='datetime',y='signal',symbol_sequence=['triangle-up','triangle-down'],name='signal')
    eqtc = go.Scatter(x=data.index,y=data['equity'],line = Line({'color': 'darkblue', 'width': 1}),name='equity')
    eqtc2 = go.Scatter(x=data.index,y=data['ema_eq'],line = Line({'color': 'red', 'width': 1}),name='EMA')
    eqtc3 = go.Scatter(x=data.index,y=data['sma_eq'],line = Line({'color': 'blue', 'width': 1}),name='SMA')
    eqtc4 = go.Scatter(x=data.index,y=data['mean_eq'],line = Line({'color': 'green', 'width': 1}),name="MEAN")
    eqtc5 = go.Scatter(x=data.index,y=data['rolling_max'],line = Line({'color': 'orange', 'width': 1}),name='Roll Max')
    eqtc6 = go.Scatter(x=data.index,y=data['rolling_min'],line = Line({'color': 'magenta', 'width': 1}),name='Roll Min')
    sigtc = go.Scatter(
        mode='markers',
        x=posdf.index,
        y=posdf['Close'],
        marker=dict(size=10,symbol=[5,6],color=['red','green']),
        name='Signal')
    acctc = go.Scatter(x=data.index,y=data['accs'],line=Line({'color': 'red', 'width': 1}),name='Acc')
    gradtc = go.Scatter(x=data.index,y=data['grads'],line=Line({'color': 'blue', 'width': 1}),name='Grad')
    data1 = [pricetc,sigtc]
    data2 = [eqtc,eqtc2,eqtc3,eqtc4,eqtc5,eqtc6]
    data4 = [acctc,gradtc]
    fig = make_subplots(rows=3, cols=1,shared_xaxes=True,subplot_titles=("Price + Signal","Equity + Measures",f"Indicators"))
    fig.add_traces(data1, rows=1, cols=1)
    fig.add_traces(data2, rows=2, cols=1)
    fig.add_traces(data4,rows=3,cols=1)
    ivls = list(outstrat.keys()) # these are intervals
    ivls.append(datetime.today().replace(minute=0,second=0,microsecond=0))
    colours = ['blue','green','red','orange','purple','blue','darkgreen','skyblue']
    # breakpoint()
    for i in range(1,len(ivls)):
        try:
            fig.add_vrect(
                x0=ivls[i-1].isoformat(sep=" "),
                x1=ivls[i].isoformat(sep=" "),
                annotation_text='/'.join([str(outstrat[ivls[i-1]]['win']),str(outstrat[ivls[i-1]]['deg'])]),
                annotation_position='top left',
                fillcolor=colours[i-1],
                opacity=0.1,
                line_width=0
            )
        except IndexError:
            breakpoint()
    fig.update_layout(title_text=f'{c} - Out-of-Sample 1-Opter Backtest - depth {md} hrs - {btd} 750 hrs - {max_trade} - 20')  
    fig.show()
    return fig

def main(c,md,btd,mt,pracc,mdd):
    M_end = datetime.today().replace(minute=0,second=0,microsecond=0)
    M_start = M_end - timedelta(hours=md+btd)
    print(M_end,M_start)
    eq = 100000
    # p is always full p dont change
    p = prices(c,M_start,M_end) # (1) Load Prices - here p is [btd+md]
    ind,ws,ds = all_indics(c,M_start,M_end) # (2) inds required for (2)
    # Sort starts and ends properly here
    istart = M_start
    iend = M_start+timedelta(hours=btd) # check
    opst = opstrat(p,ind,istart,iend,btd,eq,ws,ds,mt,pracc) # (2) opstr
    # M_end is major end, iend is the end of the initial backtest
    bigpos = pd.DataFrame()
    data,posdf = populate_columns(p,opst,eq,iend,M_end,ind,pracc)
    bigpos = pd.concat([bigpos,posdf])
    f = pd.DataFrame().reindex_like(data)
    i = min(f.index)
    outstrat = {}
    outstrat[iend] = opst
    while i != max(f.index):
        if data.loc[i]['rolling_max']==data.loc[i]['rolling_min']==data.loc[i]['equity']:
            f.loc[i] = data.loc[i]
        elif data.loc[i]['rolling_min'] > data.iloc[0]['equity'] * mdd:
            print(i,"first elif",data.loc[i]['rolling_min'] > data.iloc[0]['equity'] * mdd)
            f.loc[i] = data.loc[i]
        elif (data.loc[i]['equity'] < data.loc[i]['rolling_max']*0.99 and data.loc[i]['equity']>eq) or \
            len(list(set(list(data['equity'].loc[i-timedelta(hours=100):i]))))>1:
            print(
                i,
                "2nd elif",
                len(list(set(list(data['equity'].loc[i-timedelta(hours=100):i]))))>1,
                (data.loc[i]['equity'] < data.loc[i]['rolling_max']*0.99 and data.loc[i]['equity']>eq)
                )
            opst = opstrat(p,ind,i-timedelta(hours=btd),i,btd,data.loc[i]['equity'],ws,ds,mt,pracc)
            outstrat[i] = opst
            data,posdf = populate_columns(p,opst,data.loc[i]['equity'],i,M_end,ind,pracc)
            bigpos = pd.concat([bigpos,posdf])
            f.loc[i:] = data.loc[i:]
            f = add_metrics(f)
        else:
            f.loc[i] = data.loc[i]
            # f = add_metrics(f)
        i = i+timedelta(hours=1)
    f = add_metrics(f)

    bigpos['colour'] = ['green' if x==1 else 'red' if x==-1 else None for x in list(bigpos.presignal)]
    bigpos['symbol'] = ['triangle-up' if x==1 else 'triangle-down' if x==-1 else None for x in list(bigpos.presignal)]
    return f,opst,outstrat,bigpos


if __name__=="__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--out',
        type=str,
        required=True,
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
        args.max_drawdowndepth = 0.975
    print(args)
    global max_trades,btd,md,mdd
    pracc = 0
    max_trades = 10
    c = args.crypto
    btd = args.bt_depth # backtest depth
    md = args.depth # backtest depth
    mdd = args.max_drawdowndepth
    data,opst,outstrat,posdf = main(
        c=c,
        md=md, # model depth (what is plotted)
        btd=btd, # backtest depth,
        pracc=pracc,
        mdd=mdd
    )

    class PdEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, pd.Timestamp):
                return str(obj)
            return json.JSONEncoder.default(self, obj)
    
    csvpath = os.path.join(os.getcwd(),f'output_{c}_{datetime.today().replace(minute=0,second=0,microsecond=0).isoformat(sep="T")}.csv')
    jsonpath = os.path.join(os.getcwd(),f'output{c}_{datetime.today().replace(minute=0,second=0,microsecond=0).isoformat(sep="T")}.json')
    if args.out=='json':
        with open(jsonpath,'w') as f_out:
            json.dump(data.to_dict(orient='records'),f_out,cls=PdEncoder)
    elif args.out=='csv':
        data.to_csv(csvpath)
    elif args.out=='plotly':
        fig = plot(c,data,opst,outstrat,posdf)
    breakpoint()