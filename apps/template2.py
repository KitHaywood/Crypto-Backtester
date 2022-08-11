from dash import dcc 
from dash import html 


def app_layout():
    return html.Div(style = {
        'backgroundColor':'white'
    },children=[
        dcc.Store(id='iprices-data'),
        dcc.Store(id='posdf-data'),
        dcc.Store(id='outstrat-data'),
        html.H1(children='0-turn Model',
        style={'textAlign':'center','color':'black'}),
        html.Div(className='row',children=[
            
            html.Div(className='six columns', children=[
                html.Label(['Select Stock'],style={'text-align':'left','color':'black'}),
                    dcc.Dropdown(
                    id='crypto-selector',
                    options=['REP','XLM'],
                    value='REP'),
                html.Label(['Select in-sample Backtest Depth'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='btd-input',
                    type='number',
                    placeholder="input an integer")]),
            html.Div(className='six columns', children=[
                html.Label(['Select Model Duration (hrs)'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='md-input',
                    type='number',
                    placeholder="input an integer"),
                html.Label(['Select Max-Drawdown Threshold'],style={'text-align':'left','color':'black'}),
                    dcc.Input(
                    id='mdd-input',
                    type='number',
                    placeholder="input [0.0 -- 1.0]"),
                html.Button(id='go-button',n_clicks=0,children='Run Model')
        ])],style={'display':'flex','margin':'15px'}),
        html.Div(
            [
                dcc.Graph(id='mygraph'),
            ]
        ),
        dcc.Markdown(id='axis_data')
    ]
    )
