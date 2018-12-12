import dash
import dash_core_components as dcc
import dash_html_components as html
import datetime as dt
import pandas as pd
import plotly
import numpy as np
import plotly.graph_objs as go
from urllib.parse import quote
from dash.dependencies import Input, Output, State
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from app.configs import db_configs

conn = create_engine(URL(**db_configs()))


def fetch_data(q):
    result = pd.read_sql(
        sql=q,
        con=conn
    )
    return result


def get_wave_data(t0, t1, site_id):
    """
    Return wave data results from coolops database
    :param site_id: id number for CODAR site from `hfrSites`
    :param t0: start datetime
    :param t1: end datetime
    :return:
    """

    if not site_id:
        site_id = 28

    # Build SQL Statement to grab wave data
    sql = 'SELECT wd.MWHT, wd.MWPD, wd.WAVB, wd.WNDB, wd.datetime FROM hfrWaveData AS wd '
    sql += 'INNER JOIN hfrWaveFilesMetadata AS md ON wd.file_id = md.id '
    sql += 'WHERE wd.mwht_flag= 1 AND md.TableWaveMode = 2 AND '
    sql += "wd.site_id = {} AND wd.datetime BETWEEN '{}' and '{}'".format(site_id, t0, t1).replace('\n', ' ')

    # grab the data from the mysql database
    df = fetch_data(sql)

    # filter out bad values
    df = df[df['MWHT'] != 999.0]

    # convert from meters to feet
    df['MWHT'] = df['MWHT']*3.2808
    df['MWHT'] = df['MWHT'].round(2)
    return df


def get_site_data():
    sql = 'SELECT DISTINCT site_id, site from hfrWaveData as wd INNER JOIN hfrSites as s on wd.site_id = s.id'
    site_df = fetch_data(sql)
    sites = dict(zip(site_df.site, site_df.site_id))
    site_options = [{'label': site, 'value': sites[site]} for site in sites.keys()]
    return site_options


def serve_layout():
    layout = html.Div([
         html.Div([
             html.Div([
                 html.H1('Rutgers HFRadar Wave Viewer')
             ]),
             html.Div([
                 dcc.Dropdown(id='site-selector', options=get_site_data(), value=28)
             ], style={'width': '10%'}),
             html.Div([
                 dcc.DatePickerRange(
                     id='date-range',
                     min_date_allowed=dt.datetime(2017, 6, 1),
                     max_date_allowed=dt.datetime.today(),
                     initial_visible_month=dt.datetime.today(),
                     start_date=dt.datetime.now() - dt.timedelta(days=7),
                     end_date=dt.datetime.now())
             ]),
             html.Div([
                 html.Button('Submit', id='button'),
                 html.A('Download Data',
                        id='download-link',
                        download="rawdata.csv",
                        href="",
                        target="_blank")
             ]),
        ], style={
            'borderBottom': 'thin lightgrey solid',
            'backgroundColor': 'rgb(250, 250, 250)',
            'padding': '10px 5px'
        }),
        # Wave Height and Period Graphs
        html.Div([
            dcc.Interval(id='interval-component', interval=60000, n_intervals=0),
            dcc.Graph(id='wave_data'),
        ], className='seven columns'),
        html.Div([
            html.Div([dcc.Graph(id='wave_dir')], style={'padding': '10px 5px'}),
            html.Div([dcc.Graph(id='wind_dir')], style={'padding': '15px 5px'}),
        ], className='one columns'),
        html.Div(id='intermediate-value', style={'display': 'none'})
    ])
    return layout


def plot_polar(df, var):
    if var == 'WAVB':
        title = 'Wave from Direction'
    elif var == 'WNDB':
        title = 'Wind from Direction'

    df['rad'] = 10
    rad = np.full(5, df['rad'])
    bear = np.full(5, df[var])
    trace = go.Area(
        r=rad,
        t=bear,
        marker=go.scatter.Marker(
            color='rgb(242, 196, 247)'
        )
    )
    trace1 = go.Area(
        r=rad * 0.65,
        t=bear,
        marker=go.scatter.Marker(
            color='#F6D7F9'
        )
    )
    trace2 = go.Area(
        r=rad * 0.30,
        t=bear,
        marker=go.scatter.Marker(
            color='#FAEBFC'
        )
    )
    layout = go.Layout(
        title=title,
        autosize=True,
        width=200,
        height=200,
        plot_bgcolor='#F2F2F2',
        margin=go.Margin(
            t=50,
            b=30,
            r=30,
            l=40
        ),
        showlegend=False,
        radialaxis=dict(
            range=[0, 10]
        ),
        angularaxis=dict(
            showline=False,
            tickcolor='white'
        ),
        orientation=270,
    )
    return go.Figure(data=[trace, trace1, trace2], layout=layout)


# Set up Dashboard and call dynamic layout function
app = dash.Dash()
app.layout = serve_layout


@app.callback(
    Output('intermediate-value', 'children'),
    [Input('button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('site-selector', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')])
def clean_data(c, n, site_id, start_date, end_date):
    if not site_id:
        site_id = 28

    results = get_wave_data(start_date, end_date, site_id)
    return results.to_json()


# Update Wave Height  Graph
@app.callback(
    Output('wave_data', 'figure'),
    [Input('intermediate-value', 'children')])
def update_wave_graphs(data):
    df = pd.read_json(data)

    fig = plotly.tools.make_subplots(rows=2, cols=1, vertical_spacing=0.05, shared_xaxes=True)

    fig['layout']['margin'] = {'l': 42, 'r': 10, 'b': 20, 't': 10}
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}

    fig.append_trace({
        'x': df['datetime'],
        'y': df['MWHT'],
        'name': 'Height (feet)',
        'mode': 'markers',
        'type': 'scatter'
    }, 1, 1)
    fig.append_trace({
        'x': df['datetime'],
        'y': df['MWPD'],
        'name': 'Period (seconds)',
        'mode': 'markers',
        'type': 'scatter'
    }, 2, 1)
    fig['layout']['yaxis1'].update(title='Wave Height (ft)')
    fig['layout']['yaxis2'].update(title='Wave Period (s)')
    return fig


@app.callback(
    Output('wave_dir', 'figure'),
    [Input('wave_data', 'hoverData'),
     Input('intermediate-value', 'children')])
def plot_wave_dir(hoverdata, wave_data):
    var = 'WAVB'
    if (hoverdata is None or len(wave_data) is 0):
        return ''
    ind = hoverdata['points'][0]['x']
    df = pd.read_json(wave_data)
    df = df[df['datetime']==ind]
    fig = plot_polar(df, var)
    return fig


@app.callback(
    Output('wind_dir', 'figure'),
    [Input('wave_data', 'hoverData'),
     Input('intermediate-value', 'children')])
def plot_wind_dir(hoverdata, wave_data):
    var = 'WNDB'
    if hoverdata is None or len(wave_data) is 0:
        return ''
    ind = hoverdata['points'][0]['x']
    df = pd.read_json(wave_data)
    df = df[df['datetime']==ind]
    fig = plot_polar(df, var)
    return fig


# creates download data link for raw data
@app.callback(
    Output('download-link', 'href'),
    [Input('intermediate-value', 'children')])
def update_download_link(data):
    df = pd.read_json(data)
    csv_string = df.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + quote(csv_string)
    return csv_string


external_css = ["https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
                "https://fonts.googleapis.com/css?family=Raleway:400,400i,700,700i"]

for css in external_css:
    app.css.append_css({"external_url": css})

server = app.server

# start Flask server
if __name__ == '__main__':
    app.run_server()
