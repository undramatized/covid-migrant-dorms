import pandas as pd
import numpy as np
import geopandas as gpd
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
import math

import plotly.graph_objects as go

from bokeh.palettes import magma

import gspread
from google.oauth2.service_account import Credentials


# # Load Shape file

path = './geodata/'
areas = gpd.read_file(path + 'master-plan-2019-planning-area-boundary-no-sea-geojson.geojson')


region = []
for i in range(0,55):
    soup = BeautifulSoup(areas['Description'][i], 'html.parser').get_text()
    start = soup.find("PLN_AREA_N ") + len("PLN_AREA_N ")
    end = soup.find("PLN_AREA_C")
    region.append(soup[start:end].strip())

areas['region'] = region

areas[['Name','region','geometry']].to_json()


# # Load data from Google Sheet

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
# credentials = Credentials.from_service_account_file('sigrid-1362-f23b3afad1e2.json', scopes=scope)
credentials = Credentials.from_service_account_file('google_secrets.json', scopes=scope)
gc = gspread.authorize(credentials)
dorms = gc.open("dorms numbers")


# ## Dorms location
adresses = pd.DataFrame(dorms.worksheet("addresses").get_all_records())
adresses = adresses[adresses['Latitude']!='']

# ## Nb of cases

dfmarch = pd.DataFrame(dorms.worksheet("March").get_all_records())
dfapril = pd.DataFrame(dorms.worksheet("April").get_all_records())

dfall = pd.concat([dfmarch[['Date ','Dorms','New Cases','Cumulative total']],dfapril[['Date ','Dorms','New Cases','Cumulative total']]])
dfall.columns = ['date', 'dorms', 'newcases', 'cumtot']
dfall = dfall[dfall['date']!='']
dfall = dfall[dfall['newcases']!='']
dfall['cumtot'][dfall['cumtot']==''] = 0
dfall['date'] = [datetime.strptime(str(x), '%d/%m/%Y') for x in dfall['date']]

data = pd.merge(dfall,adresses,how = 'left', left_on = 'dorms', right_on = 'Name')
data['sizes'] = 10 + data['newcases'].astype(int) / 4


col = []
for val in data['newcases']:
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
data['colors'] = col


data.columns = ['date', 'dorms', 'newcases', 'cumtot', 'Name', 'Address', 'y',
       'x', 'sizes', 'colors']


stdt = datetime.date(min(data['date']))
eddt = datetime.date(max(data['date']))
stp = (eddt-stdt).days

data['date2'] = [(datetime.date(x)-stdt).days for x in data['date']]


# # Overall data for chart

nbcases = dfall.groupby('date')['newcases'].sum().reset_index()
nbcases = nbcases[nbcases['newcases']!='']
nbcases['cumtot'] = nbcases['newcases'].cumsum()
nbcases = nbcases.reset_index()


# # Top 10 dorms per cumulative numbers

upcases = dfall[['dorms','newcases']][dfall['date'] == eddt]
upcases.columns = ['dorms','up']

topdorms = dfall.groupby('dorms')['newcases'].sum().reset_index()
topdorms = topdorms[topdorms['newcases']!='']
topdorms = topdorms.sort_values(by = 'newcases', ascending = False)
topdorms0 = topdorms[topdorms['newcases']==0]
topdorms = pd.merge(topdorms,upcases, how = 'left')
topdorms = topdorms.fillna(0)
topdorms = topdorms[topdorms['newcases']>0]
topdorms


lastdata0 = pd.merge(topdorms0, adresses, how = 'left', left_on = 'dorms', right_on = 'Name')
lastdata0 = lastdata0[~pd.isnull(lastdata0['Latitude'])]
lastdata0.columns = ['dorms', 'newcases', 'Name', 'Address', 'y', 'x']

lastdata = pd.merge(topdorms, adresses, how = 'left', left_on = 'dorms', right_on = 'Name')
lastdata['sizes'] = 10 + lastdata['newcases'].astype(int) / 4
col = []
for val in lastdata['newcases']:
    if (val < 10):
        col0 = '#FFFFFF'
    elif (val < 20):
        col0 = '#fffcad'
    elif (val < 30):
        col0 = '#ffe577'
    elif (val < 40):
        col0 = '#ffcf86'
    elif (val < 50):
        col0 = '#fda63a'
    else:
        col0 = '#ff5a00'
    col.append(col0)
lastdata['colors'] = col

lastdata.columns = ['dorms', 'newcases', 'up', 'Name', 'Address', 'y', 'x','sizes', 'colors']

# # Transpose data for Area chart
tmp = data[data['dorms'].isin(lastdata['dorms'].to_list())]
tmp['newcases'] = tmp['newcases'].astype(int)

area_data = tmp[['date','dorms','newcases']].set_index(['date','dorms'], drop = True).unstack('dorms').reset_index()
area_data = area_data.fillna(0)
a1 = area_data['newcases'].cumsum()
area_data = pd.concat([area_data['date'],a1], axis = 1)
xcols = ['date'] + lastdata['dorms'].to_list()
area_data = area_data[xcols]


# # Map with plotly

sgmap = go.Figure()
sgmap.add_trace(go.Scattermapbox(
        lat=lastdata["y"],
        lon=lastdata["x"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=lastdata['newcases'].astype(int)*1.1,
            color = "black", opacity=0.7
        ),
        hoverinfo='none'
))
sgmap.add_trace(go.Scattermapbox(
        lat=lastdata["y"],
        lon=lastdata["x"],
        customdata=lastdata["dorms"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=lastdata['newcases'],
            color = lastdata['colors'], opacity=0.9
        ),
        hovertemplate = '<br><b>%{customdata} </b><br>' + "Total Cases: %{marker.size:,}",
))
sgmap.add_trace(go.Scattermapbox(
        lat=lastdata0["y"],
        lon=lastdata0["x"],
        customdata=lastdata0["dorms"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=6,
            color = 'black'
        ),
        hovertemplate = '<br><b>%{customdata} </b><br>' + "Total Cases: 0",
    ))

sgmap.update_traces(
    mode='markers',
    marker={'sizemode':'area',
            'sizeref':0.1})

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
    showlegend=False
)

sgmap.update_layout(mapbox_style="carto-positron")
sgmap.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
# sgmap.show()
# sgmap.write_html("Map.html")


# # Bar chart in plotly
nbcases['tooltip'] = [x.strftime("%d %b") for x in nbcases['date']]

chart1 = go.Figure()

chart1.add_trace(
    go.Scatter(
        x=nbcases['date'],
        y=nbcases['cumtot'],
        line=dict(color='#00bcd4', width=2),
        mode='lines+markers',
        name='Total cases',
        hovertemplate = '%{y}',
))


chart1.add_trace(
    go.Bar(
        x=nbcases['date'],
        y=nbcases['newcases'],
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
    yaxis_showgrid=True
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
# chart1.write_html("CumulativeChart.html")


# # Area chart in plotly
tp = area_data[['date']+[x for x in area_data.columns[1:-1]][::-1]]
area_data2 = (tp.set_index('date').stack()).reset_index()
area_data2.columns = ['date','dorms','cumtot']
area_data2.head()

chart2 = go.Figure()

acol = magma(area_data.shape[1]-2)[::-1]

for i in reversed(range(area_data.shape[1]-2)):
    # print("THIS IS AREA_DATA:", area_data)
    yname = area_data.drop(['date'], axis = 1).columns[i]
    y = area_data.drop(['date'], axis = 1)[yname]
    chart2.add_trace(go.Scatter(
        x=area_data['date'], y=y,
        mode='lines',
        line=dict(width=0.5, color=acol[i]),
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
    legend=dict(orientation='h', x = 0,y = -0.8, yanchor='bottom')
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
# chart2.write_html("AreaChart.html")


# # Table in plotly

area_data['tooltip'] = [x.strftime("%d %b") for x in area_data['date']]

tab = go.Figure(data=[go.Table(
    columnwidth = 50,
    header=dict(values=list(area_data.columns[:-1]),
                line_color='darkslategray',
                fill_color='lightgrey',
                align='left'),
    cells=dict(values=[area_data['tooltip']] + [area_data[col] for col in area_data.columns[1:-1]],
               fill_color='whitesmoke',
               line_color='darkslategray',
               align='right'))
])

tab.update_layout(
    width=1700,
    height=500,
    margin=dict(
        l=1,
        r=1,
        pad=4
    ),
)

# tab.show()
# tab.write_html("Table.html")

# APP SERVER
import dash
import dash_core_components as dcc
import dash_html_components as html


fonts_path = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap'
app = dash.Dash(__name__, external_stylesheets=[fonts_path])

server = app.server

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

        dcc.Graph(
            id='cases-graph',
            className='chart-component',
            figure=chart1
        ),

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
