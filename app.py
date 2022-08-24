#----------------------- STANDARD DASH DEPENDENCIES ---------------------------#

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

#----------------------- THIS APP'S DEPENDENCIES ------------------------------#

import json
import numpy as np
import pandas as pd
import plotly.express as px
from shapely.geometry import MultiPolygon, shape

#----------------------- LOCAL APP DEPENDENCIES -------------------------------#

from settings import mapbox_token, mode_bar_config

#----------------------- CONSTANTS AND DATA -----------------------------------#

GEO = json.load(open("data/blocks.geojson"))
DF = pd.DataFrame.from_records([f['properties'] for f in GEO['features']])
BLOCK_LIST = sorted(DF['BlockName'].unique())
BASIN_LIST = sorted(DF['Basin'].unique())
COLORS = px.colors.qualitative.D3[:len(BLOCK_LIST)]
MAP_OPTIONS = {
    'Satellite Image': 'mapbox://styles/ccervone/cl67dlb1h001k14qct08obk0a',
    'Roads & Places': 'mapbox://styles/ccervone/cl76p13ph001414kxg4ls0nnp'
}
DEFAULT_MAP = 'Roads & Places'

#----------------------- HELPER FUNCTIONS -------------------------------------#

def filter_geo_data(block_list):
    return {
        'type': GEO['type'],
        'crs': GEO['crs'],
        'features': [
            f for f in GEO['features']
            if f['properties']['BlockName'] in block_list
        ]
    }


def unify_sourcing_area(geo_data):
    polys = [shape(f['geometry']) for f in geo_data['features']]
    unified_poly = MultiPolygon(polys)
    return unified_poly


def calc_mapbox_zoom(polygon):
    x1, y1, x2, y2 = polygon.bounds
    max_bound = max(abs(x1-x2), abs(y1-y2)) * 111
    zoom = 11.5 - np.log(max_bound)
    return zoom


def make_map(block_list, opacity=.5, maptype=DEFAULT_MAP):

    data_frame = (DF[DF['BlockName']
                  .isin(block_list)]
                  .sort_values(by='Basin'))
    total_area = data_frame['Area_sqKm'].sum()

    geo_data = filter_geo_data(block_list)
    polygon = unify_sourcing_area(geo_data)
    center_x, center_y = list(polygon.centroid.coords)[0]
    zoom = calc_mapbox_zoom(polygon)

    fig = px.choropleth_mapbox(
        data_frame=data_frame,
        geojson=geo_data,
        featureidkey='properties.BlockName',
        locations='BlockName',
        color='Basin',
        opacity=opacity,
        custom_data=['BlockName', 'Area_sqKm'],
        color_discrete_map=dict(zip(BASIN_LIST, COLORS))  
    )
    fig.update_layout(
        mapbox=dict(
            center=dict(lat=center_y, lon=center_x),
            zoom=zoom,
            accesstoken=mapbox_token,
            style=MAP_OPTIONS.get(maptype, DEFAULT_MAP)
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_showscale=False,
        legend=dict(x=0.005, y=.995)
    )
    fig.update_traces(
        marker_line=dict(color='black', width=1),
        hovertemplate="<br>".join([
            "<b>%{customdata[0]}</b>",
            "Area: %{customdata[1]:,.0f} sq-km",
        ])
    )
    return fig
    

#----------------------- APP LAYOUT -------------------------------------------#


sidebar = html.Div(
    [
        html.Div(
            html.Img(src="assets/redemption_dao_logo.jpg", style={"width": "50%"}),
            style={"textAlign": "center"}
        ),
        html.Br(),
        html.Div(
            [             
                html.P("Map Type", style={"display": "inline-block", "fontSize": "small"}),
                dcc.Dropdown(
                    id="map-select",
                    options=[{"label": x, "value": x} for x in MAP_OPTIONS.keys()],
                    value=DEFAULT_MAP,
                    style={"margin-left": "1px", "width": "14rem", "fontSize": "small"},                    
                ),    
                html.P("Basin Name", style={"margin-top": "14px", "fontSize": "small"}),
                dcc.Dropdown(
                    id="basin-select",
                    options=[{"label": x, "value": x} for x in BASIN_LIST],
                    value=BASIN_LIST,
                    style={"margin-left": "1px", "width": "14rem", "fontSize": "small"},
                    multi=True
                ),
                html.P("Block Name", style={"margin-top": "14px", "fontSize": "small"}),
                dcc.Dropdown(
                    id="block-select",
                    style={"margin-left": "1px", "width": "14rem", "fontSize": "small"},
                    multi=True
                ),
                html.P("Adjust Opacity", style={"margin-top": "14px", "fontSize": "small"}),
                dcc.Slider(
                    0, 100, 10,
                    value=50, 
                    id='opacity-slider',
                    marks={
                        0: {'label': '0%'},
                        25: {'label': '25%'},
                        50: {'label': '50%'},
                        75: {'label': '75%'},
                        100: {'label': '100%'},
                    },
                ),
            ]
        ),
        html.Br(),
        html.Hr(),
        html.H6("Source:"),
        html.Label([
            html.A("DRC Bid Round 2022 Documents",
            href="https://www.drcbidround2022.com/documents"),
        ], style={"fontSize": "small"}),
    ],
    style={
        "position": "fixed",
        "overflow": "scroll", 
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    }
)



#----------------------- CONTENT ----------------------------------------------#

content = html.Div(
    id="map-content",
    children=dcc.Graph(
        id='congo-map',
        figure=make_map(BLOCK_LIST),
        style={'height': '100vh', 'width': '100%'},
    ),
    style={
        "margin-left": "16rem",
        "margin-right": "0rem",
        "margin-top": "0rem",
        "margin-bottom": "0rem",
        "padding": "0rem",
    }
)

#----------------------- APP SET-UP -------------------------------------------#

app = dash.Dash(__name__, suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Congo Basin Map"
app.layout = html.Div([content, sidebar])

#----------------------- CALLBACKS --------------------------------------------#

@app.callback(
    [Output('block-select', 'options'), Output('block-select', 'value')],
    Input('basin-select', 'value')
)
def update_block_dropdown(basin_list):
    if basin_list is None or not len(basin_list):
        raise PreventUpdate
    block_list = DF[DF['Basin'].isin(basin_list)]['BlockName'].unique()
    options = [{'label': i, 'value': i} for i in block_list]
    return options, block_list


@app.callback(
    Output('congo-map', 'figure'),
    [Input('block-select', 'value'), Input('opacity-slider', 'value'), Input('map-select', 'value')],
)
def update_dashboard(block_list, opacity, maptype):
    if block_list is None or not len(block_list):
        raise PreventUpdate
    return make_map(block_list, opacity=opacity/100, maptype=maptype)

#----------------------- RUN --------------------------------------------------#

if __name__ == "__main__":
    app.run_server(debug=True)
