import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import ssl
import pandas as pd
from dash.dependencies import Input, Output

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

ssl._create_default_https_context = ssl._create_unverified_context
colors = {'background': '#111111',
          'text': '#7FDBFF'}

df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv")

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

#Sets df1 for graph1
df1 = df[['Date', 'AAPL.Open', 'AAPL.High']]
df1.columns = ['Date', 'Activity', 'Baseline']

#Sets df2 for graph2
df2 = df[['Date', 'AAPL.Volume']]
df2.columns = ['Date', 'Volume']

#App layout
app.layout = html.Div(style={'backgroundColor': colors['background']}, 
                      children=[
    
    html.H1(children='graph1',
            style={'textAlign': 'center',
                   'color': colors['text']}),

    html.Div(children='Displaying Apple High and Low.', 
             style={'textAlign': 'center',
                    'color': colors['text']}),

    dcc.Graph(id='graph1'),

    html.Div(children='Second Graph (Volume).', 
             style={'textAlign': 'center',
                    'color': colors['text']}),
    dcc.Graph(id='graph2'),
    
    #item to track x axis relayout data
    dcc.Markdown(id= 'axis_data'),

])

@app.callback(
    Output('graph2', 'figure'),
    Input('graph1', 'relayoutData'))

def relayout_graph2(xaxis_config):

    figure2 = go.Figure()
    figure2.add_trace(go.Scatter(x = df2.Date, y = df2.Volume, name = 'Volume'))
    figure2.update_layout(plot_bgcolor = colors['background'],
                          paper_bgcolor = colors['background'],
                          font_color = colors['text'],
                          showlegend = True)
    
    if not xaxis_config:
        pass
    
    else:
        #For some reason it's necessary to convert the relayout dict keys to strings
        keys_values = xaxis_config.items()
        xaxis = {str(key): value for key, value in keys_values}
        try:
            if 'autosize' in xaxis.keys():
                pass
            elif 'xaxis.autorange' in xaxis.keys():
                figure2.update_xaxes(autorange = True)
            else:
                figure2.update_xaxes(range=[xaxis['xaxis.range[0]'],xaxis['xaxis.range[1]']])
        except:
            pass
    
    return figure2

@app.callback(
    Output('graph1', 'figure'),
    Input('graph2', 'relayoutData'))

def relayout_graph1(xaxis_config):

    figure1 = go.Figure()
    figure1.add_trace(go.Scatter(x = df1.Date, y = df1.Activity, name = 'Activity'))
    figure1.add_trace(go.Scatter(x = df1.Date, y = df1.Baseline, name = 'Baseline'))
    figure1.update_layout(plot_bgcolor = colors['background'],
                          paper_bgcolor = colors['background'],
                          font_color = colors['text'])
    
    if not xaxis_config:
        pass
    
    else:
        
        #For some reason it's necessary to convert the relayout dict keys to strings
        keys_values = xaxis_config.items()
        xaxis = {str(key): value for key, value in keys_values}
        
        try:
            if 'autosize' in xaxis.keys():
                pass
            elif 'xaxis.autorange' in xaxis.keys():
                figure1.update_xaxes(autorange = True)
            else:
                figure1.update_xaxes(range=[xaxis['xaxis.range[0]'],xaxis['xaxis.range[1]']])
        
        except:
            pass
    
    return figure1

@app.callback(
    Output('axis_data', 'children'),
    [Input('graph1', 'relayoutData'),
     Input('graph2', 'relayoutData')])

def read_relayout(data1, data2):
    
    return str(data1) + '///' + str(data2)

if __name__ == '__main__':
    app.run_server(debug=True, port = 8888)