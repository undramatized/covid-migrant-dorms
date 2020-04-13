import pandas as pd
import numpy as np
import geopandas as gpd
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
import math
from dotenv import load_dotenv
load_dotenv()

import plotly.graph_objects as go

from bokeh.palettes import magma

import gspread
from google.oauth2.service_account import Credentials


from plotly.offline import download_plotlyjs, init_notebook_mode, iplot
from plotly.graph_objs import *
#init_notebook_mode()


# # Load data from Google Sheet

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = Credentials.from_service_account_file(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scopes=scope)
gc = gspread.authorize(credentials)
dorms = gc.open("dorms numbers")
# All Data
alldata = pd.DataFrame(dorms.worksheet("AllCases").get_all_records())
alldata['NewCases'].replace('','0',inplace=True)
alldata = alldata.astype({'Dorms':'str','Address':'str','Latitude':'float64','Longitude':'float64',
                'NewCases':'int','CumulativeByDorm': 'int'})
alldata['Date'] = [datetime.strptime(str(x), '%d/%m/%Y') for x in alldata['Date']]
col = []
for val in alldata['CumulativeByDorm']:
    if (val < 5):
        col0 = '#FFFFFF'
    elif (val < 10):
        col0 = '#fffcad'
    elif (val < 15):
        col0 = '#ffe577'
    elif (val < 20):
        col0 = '#ffcf86'
    elif (val < 25):
        col0 = '#fda63a'
    else:
        col0 = '#ff5a00'
    col.append(col0)
alldata['colors'] = col


# Data prep for the map
mapdata = alldata[alldata['Date'] == max(alldata['Date'])]
mapdata1 = mapdata[mapdata['CumulativeByDorm']>0]
mapdata1 = mapdata1.sort_values(by = 'CumulativeByDorm', ascending = False)
mapdata0 = mapdata[mapdata['CumulativeByDorm']==0]

# Transpose data for Area chart
tmp = alldata[alldata['Dorms'].isin(mapdata1['Dorms'].to_list())]

transdata = tmp[['Date','Dorms','NewCases']].set_index(['Date','Dorms'], drop = True).unstack('Dorms').reset_index()
transdata = transdata.fillna(0)
a1 = transdata['NewCases'].cumsum()
transdata = pd.concat([transdata['Date'],a1], axis = 1)
xcols = ['Date'] + mapdata1['Dorms'].to_list()
transdata = transdata[xcols]


# # Map with plotly

# Initialize figure
sgmap = go.Figure()
# This adds a black outline to the circles on the map
sgmap.add_trace(go.Scattermapbox(
        lat=mapdata1["Latitude"],
        lon=mapdata1["Longitude"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=mapdata1['CumulativeByDorm']*1.1,
            color = "black", opacity=0.7
        ),
        hoverinfo='none'
))
# Add circles on map, with size and color changing with cumulative numbers
sgmap.add_trace(go.Scattermapbox(
        lat=mapdata1["Latitude"],
        lon=mapdata1["Longitude"],
        customdata=mapdata1["Dorms"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=mapdata1['CumulativeByDorm'],
            color = mapdata1['colors'], opacity=0.9
        ),
        hovertemplate = '<br><b>%{customdata} </b><br>' + "Total Cases: %{marker.size:,}",
        name = '',
))
# Add small black circles for dorms witn no cases
sgmap.add_trace(go.Scattermapbox(
        lat=mapdata0["Latitude"],
        lon=mapdata0["Longitude"],
        customdata=mapdata0["Dorms"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=6,
            color = 'black'
        ),
        hovertemplate = '<br><b>%{customdata} </b><br>' + "Total Cases: 0",
        name = '',
    ))
# Resize the circles
sgmap.update_traces(
    mode='markers',
    marker={'sizemode':'area',
            'sizeref':0.1})
# Layout update, centers the map, zoom in onto the map
sgmap.update_layout(
    hovermode='closest',
    mapbox=dict(
        #accesstoken=mapbox_access_token,
        bearing=0,
        center=go.layout.mapbox.Center(
            lat=1.348839,
            lon=103.823308
        ),
        pitch=0,
        zoom=10.5
    ),
    showlegend=False,
    xaxis_fixedrange=True,
    yaxis_fixedrange=True,

)

sgmap.update_layout(mapbox_style="carto-positron") # style of the mapbox
sgmap.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # reduce margins
# sgmap.show()
#sgmap.write_html("Map.html")


# # Bar chart in plotly
nbcases = alldata.groupby('Date')['NewCases'].sum().reset_index()
nbcases = nbcases[nbcases['NewCases']!='']
nbcases['CumulativeByDorm'] = nbcases['NewCases'].cumsum()
nbcases = nbcases.reset_index()
nbcases['tooltip'] = [x.strftime("%d %b") for x in nbcases['Date']]

#alldata['tooltip'] = [x.strftime("%d %b") for x in alldata['Date']]

# Initialize figure
chart1 = go.Figure()
# Line chart
chart1.add_trace(
    go.Scatter(
        x=nbcases['Date'],
        y=nbcases['CumulativeByDorm'],
        line=dict(color='#00bcd4', width=2),
        mode='lines+markers',
        name='Total cases',
        hovertemplate = '%{y}',
))


chart1.add_trace(
    go.Bar(
        x=nbcases['Date'],
        y=nbcases['NewCases'],
        name = 'New cases',
        marker_color = '#b2ebf2',
        hovertemplate = '%{y}',
    hoverinfo ='text')
)

chart1.update_layout(
    title_text="Number of cases over time",
    height=500,
    width=900,
    template="plotly_white",
    hovermode='x unified',
    xaxis_showgrid=True,
    yaxis_showgrid=True,
    xaxis_fixedrange=True,
    yaxis_fixedrange=True,
)
chart1.update_xaxes(tickangle=-45,
                tickmode='linear',
                ticks="outside",
               showline=True,
               rangemode="tozero")
chart1.update_yaxes(ticks="outside",
               showline=True,
                rangemode="tozero")

# chart1.show()
#chart1.write_html("CumulativeChart.html")


# # Area chart in plotly
transdata['tooltip'] = [x.strftime("%d %b") for x in transdata['Date']]
acol = magma(transdata.shape[1]-2)[::-1]

# Initialize the figure
chart2 = go.Figure()
# Area chart for each series
for i in reversed(range(transdata.shape[1]-2)):
    yname = transdata.drop(['Date','tooltip'], axis = 1).columns[i]
    y = transdata.drop(['Date','tooltip'], axis = 1)[yname]
    chart2.add_trace(go.Scatter(
        x=transdata['Date'],
        y=y,
        mode='lines',
        line=dict(width=0.5, color='lightgray'),
        fillcolor=acol[i],
        stackgroup='one',
        name = yname,
        hovertemplate = '%{y}',
    ))

chart2.update_layout(
    title_text="Number of cases over time",
    height=700,
    width=900,
    template="plotly_white",
    hovermode='x unified',
    xaxis_showgrid=True,
    yaxis_showgrid=True,
    xaxis_fixedrange=True,
    yaxis_fixedrange=True,
    legend=dict(orientation='h', x = 0,y = -1.2, yanchor='bottom')
)

chart2.update_xaxes(tickangle=-45,
                tickmode='linear',
                ticks="outside",
               showline=True,
               rangemode="tozero")
chart2.update_yaxes(ticks="outside",
               showline=True,
                rangemode="tozero")

# chart2.show()
#chart2.write_html("AreaChart.html")


# # Table in plotly

#area_data['tooltip'] = [x.strftime("%d %b") for x in area_data['date']]

tab = go.Figure(data=[go.Table(
    columnwidth = 50,
    header=dict(values=list(transdata.columns[:-1]),
                line_color='darkslategray',
                fill_color='lightgrey',
                align='left'),
    cells=dict(values=[transdata['tooltip']] + [transdata[col] for col in transdata.columns[1:-1]],
               fill_color='whitesmoke',
               line_color='darkslategray',
               align='right'))
])

tab.update_layout(
    title_text="Detailed Number of cases per Dorm over Time",
    width=1700,
    height=600,
    margin=dict(
        l=1,
        r=1,
        pad=4
    ),
)

# tab.show()
#tab.write_html("Table.html")



# APP SERVER
import dash
import dash_core_components as dcc
import dash_html_components as html


fonts_path = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap'
app = dash.Dash(__name__, external_stylesheets=[fonts_path])

server = app.server

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>COVID19 Migrant Worker Dorms</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <div>Made with <span style="color: #e25555;">&hearts;</span> in Singapore</div>
    </body>
</html>
'''

app.layout = html.Div(children=[
    html.H2(children='COVID19 - Migrant Worker Dorm Infections'),

    html.Div(children='''
        A dashboard to visualise the infections across foreign worker dormitories.
    '''),

    html.Div(className='container',
        children=[
        dcc.Graph(
            id='map-graph',
            className='map-component',
            figure=sgmap
        ),

        html.Div(className='chart-container',
        children=[
            dcc.Graph(
            id='cases-graph',
            className='chart-component',
            figure=chart1
            ),

            html.P(className='usage-tip',
            children='For mobile usage: \nTap anywhere on the chart to see details in a popover.\nSlide or pinch on chart to remove the popover.'),
        ]),

        dcc.Graph(
            id='dorm-area-graph',
            className='chart-component',
            figure=chart2
        ),

        dcc.Graph(
            id='data-table',
            className='table-component',
            figure=tab
        ),

    ])

])

if __name__ == '__main__':
    app.run_server(debug=True)
