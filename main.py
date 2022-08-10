from dash.dependencies import Input, Output, State
from plotly.graph_objects import Scatter
import numpy as np
import plotly.express as px 
from apps.template import app_layout
import datetime as dt
from apps.app import dash_app
import pandas as pd
from utils import *
import pdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from signaller import *
import json

dash_app = dash_app
dash_app.layout = app_layout()
app = dash_app.server

@dash_app.callback(
    [Output('iprices-data', 'data'),Output('posdf-data','data'),Output('outstrat-data','data')], Input('go-button', 'n_clicks'),
    [State('crypto-selector','value'),State('btd-input','value'),
     State('md-input','value'),State('mdd-input','value')]
)
def get_data(n,c,btd,md,mdd):
    data,opst,outstrat,posdf = main(c=c,md=md,btd=btd)
    print(data,posdf)
    newout = {}
    for k,v in outstrat.items():
        newk = dt.datetime.strftime(k,"%Y-%m-%d %H:%M:%S")
        newout[newk] = v
        
    return data.to_json(date_format='iso', orient='split'),posdf.to_json(date_format='iso', orient='split'),json.dumps(newout,default=str)

@dash_app.callback(
    Output(component_id='price-chart',component_property='figure'),
    [Input('iprices-data','data'),Input('posdf-data','data')]
)
def update_price_chart(data,posdf):
    posdf = pd.read_json(posdf,orient='split')
    newd = pd.read_json(data,orient='split')
    price_fig = px.line(newd,x=newd.index,y='Close',template='simple_white')
    posdf['marker_size'] = [10 for _ in range(posdf.shape[0])]
    print(posdf)
    sig_fig = px.scatter(
        posdf,
        x=posdf.index,
        y='Close',
        size='marker_size',
        symbol='signal',
        symbol_sequence=['triangle-up','triangle-down'],
        color='colour'
        )
    fig = go.Figure(data=price_fig.data + sig_fig.data)
    fig.update_layout(
        template='simple_white'
    )
    return fig

@dash_app.callback(
    Output(component_id='equity-chart',component_property='figure'),
    Input('iprices-data','data')
    )
def update_equity_chart(data):
    newd = pd.read_json(data,orient='split')
    fig = px.line(newd,x=newd.index,y='equity',template='simple_white')
    return fig

@dash_app.callback(
    Output(component_id='signal-chart',component_property='figure'),
    [Input('iprices-data','data'),Input('outstrat-data','data')]
)
def update_signal_chart(data,outstrat):
    outstrat = json.loads(outstrat)
    newstrat = {}
    for k,v in outstrat.items():
        newk = dt.datetime.strptime(k,"%Y-%m-%d %H:%M:%S")
        newstrat[newk] = v
    print(outstrat)
    newd = pd.read_json(data,orient='split')
    accfig = px.line(newd,x=newd.index,y=['grads','accs'],color_discrete_map={
                 "grads": "blue",
                 "accs": "red"
             },template='simple_white')
    ivls = list(newstrat.keys()) # these are intervals
    ivls.append(datetime.today().replace(minute=0,second=0,microsecond=0))
    colours = ['blue','green','red','orange','purple','blue','darkgreen','skyblue']
    # breakpoint()
    for i in range(1,len(ivls)):
        try:
            accfig.add_vrect(
                x0=ivls[i-1].isoformat(sep=" "),
                x1=ivls[i].isoformat(sep=" "),
                annotation_text='/'.join([str(newstrat[ivls[i-1]]['win']),str(newstrat[ivls[i-1]]['deg'])]),
                annotation_position='top left',
                fillcolor=colours[i-1],
                opacity=0.1,
                line_width=0
            )
        except IndexError:
            breakpoint()
            
    accfig.add_hline(y=0)
    return accfig

if __name__=="__main__":
    dash_app.run_server(host='0.0.0.0',threaded=True, debug=True, port=7080)
