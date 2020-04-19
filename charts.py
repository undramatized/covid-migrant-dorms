from bs4 import BeautifulSoup
from datetime import datetime
import math
import pandas as pd
import json
import os
import requests
import datetime
from dotenv import load_dotenv
load_dotenv()

import plotly.graph_objects as go

from bokeh.palettes import magma

import gspread
from google.oauth2.service_account import Credentials

#from plotly.offline import download_plotlyjs, init_notebook_mode, iplot
#from plotly.graph_objs import *
from pylab import *


# Load data from Google Sheet
def load_data_fromJSON():
    # Load JSON file
    jsonfile = "https://raw.githubusercontent.com/wentjun/covid-19-sg/feature/covid-migrant-dorm-support/src/data/covid-sg.json"
    response = json.loads(requests.get(jsonfile).text)
    
    ids = []
    dates = []
    clusters = []
    nationality = []
    permit = []
    nclust = []
    for res in response['features']:
        ids.append(res['properties']['id'])
        dates.append(res['properties']['confirmed'])
        pm = res['properties']['nationality'].split('(')
        if len(pm)==2:
            permit.append(pm[1].replace(')',''))
            nationality.append(pm[0])
        else:
            permit.append('')
            nationality.append(pm[0])
        if res['properties']['clusters']==[]:
            clusters.append([''])
            nb = len([''])
        else:
            clusters.append(res['properties']['clusters'])
            nb = len(res['properties']['clusters'])
        nclust.append(nb)
    
    rowid = list(range(1,len(ids)+1))
    rowid_expand = [[x]*y for x,y in zip(rowid,nclust)]
    ids_expand = [[x]*y for x,y in zip(ids,nclust)]
    dates_expand = [[x]*y for x,y in zip(dates,nclust)]
    nationality_expand = [[x]*y for x,y in zip(nationality,nclust)]
    permit_expand = [[x]*y for x,y in zip(permit,nclust)]
    # ordering issue!!! 
    
    ids_flatten = [item for y in ids_expand for item in y]
    rowid_flatten = [item for y in rowid_expand for item in y]
    dates_flatten = [item for y in dates_expand for item in y]
    clusters_flatten = [item for y in clusters for item in y]
    nationality_flatten = [item for y in nationality_expand for item in y]
    permit_flatten = [item for y in permit_expand for item in y]
    
    allcases = pd.DataFrame({'RowId':rowid_flatten,'Id':ids_flatten,'Date':dates_flatten,'Cluster':clusters_flatten,'Nationality':nationality_flatten,'Permit':permit_flatten})
    allcases['Date'] = [datetime.datetime.strptime(str(x), '%Y-%m-%d') for x in allcases['Date']]
    return allcases


# Load data from Google Sheet
def load_data_fromGsheet(allcases):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_file(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scopes=scope)
    gc = gspread.authorize(credentials)
    dorms = gc.open("dorms numbers")
    refclusters = pd.DataFrame(dorms.worksheet("clusters").get_all_records())
    
    migclusters = refclusters[refclusters['MigrantRelated']=='y']
    # expand to all dates
    dts = list(allcases['Date'].unique())
    migclusters_expd = pd.DataFrame()
    migclusters_expd = pd.concat([migclusters[['Name','Latitude','Longitude']]]*len(dts), ignore_index=True) 
    dts_exp = [[x]*migclusters.shape[0] for x in dts]
    migclusters_expd['Date'] = [item for y in dts_exp for item in y]
    
    return [refclusters,migclusters,migclusters_expd]


def source_data(allcases,refclusters):
    # merge 2 datasets
    data = pd.merge(allcases,refclusters, how = 'left', left_on = 'Cluster', right_on = 'Name')
    return data


# Data prep for the map
def getmapdata(data,migclusters, migclusters_expd):
    # data for map
    mapdata0 = data[data['MigrantRelated'] == 'y'].groupby(['Date','Name','Latitude','Longitude']).size().reset_index(name='NewCases')
    mapdata = pd.merge(migclusters_expd[['Date','Name']],mapdata0[['Date','Name','NewCases']], how = 'left')
    mapdata = pd.merge(mapdata,migclusters[['Name','Latitude','Longitude']], how = 'left', on = 'Name')
    mapdata['NewCases'][pd.isnull(mapdata['NewCases'])] = 0
    mapdata['CumulativeByDorm'] = mapdata.groupby(['Date','Name','Latitude','Longitude']).sum().groupby(level=1).cumsum()['NewCases'].tolist()
    mapdata = mapdata[mapdata['Date'] == max(mapdata['Date'])]
    mapdata = mapdata.sort_values(by = 'CumulativeByDorm', ascending = False)
    # add colors
    cmap = cm.get_cmap('YlOrRd', max(mapdata['CumulativeByDorm'])+200)
    palette = []
    for i in range(cmap.N):
        rgb = cmap(i)[:3] # will return rgba, we take only first 3 so we get rgb
        palette.append(matplotlib.colors.rgb2hex(rgb))
    
    col = []
    for val in mapdata['CumulativeByDorm']:
        col.append(palette[int(val)-1])
    mapdata['colors'] = col
    return mapdata
    

def gettransdata(data,migclusters, migclusters_expd, mapdata):
# Data for area chart: transposed matrix
    chartdata = data[data['IsDorm']=='y'].groupby(['RowId','Id','Date','IsDorm'])['Name'].first().reset_index()
    areadata0 = chartdata[chartdata['IsDorm'] == 'y'].groupby(['Date','Name']).size().reset_index(name='NewCases')
    areadata = pd.merge(migclusters_expd[['Date','Name']],areadata0[['Date','Name','NewCases']], how = 'left')
    areadata = pd.merge(areadata,migclusters[['Name']], how = 'left', on = 'Name')
    areadata['NewCases'][pd.isnull(areadata['NewCases'])] = 0
    areadata['CumulativeByDorm'] = areadata.groupby(['Date','Name']).sum().groupby(level=1).cumsum()['NewCases'].tolist()
    areadata = areadata[areadata['Date']>=min(chartdata['Date'])]
    
    transdata = areadata[['Date','Name','NewCases']].set_index(['Date','Name'], drop = True).unstack('Name').reset_index()
    transdata = transdata.fillna(0)
    a1 = transdata['NewCases'].cumsum()
    transdata = pd.concat([transdata['Date'],a1], axis = 1)
    
    xcols = ['Date'] + mapdata.sort_values(by='CumulativeByDorm', ascending = False)['Name'].to_list()
    transdata = transdata[xcols]
    transdata['tooltip'] = [x.strftime("%d %b") for x in transdata['Date']]
    return transdata


## Plot Map
def getmapchart(mapdata):
# Initialize figure
    sgmap = go.Figure()
    # This adds a black outline to the circles on the map
    sgmap.add_trace(go.Scattermapbox(
            lat=mapdata["Latitude"],
            lon=mapdata["Longitude"],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=mapdata['CumulativeByDorm']*1.1,
                color = "black", opacity=0.6
            ),
            hoverinfo='none'
    ))
    # Add circles on map, with size and color changing with cumulative numbers
    sgmap.add_trace(go.Scattermapbox(
            lat=mapdata["Latitude"],
            lon=mapdata["Longitude"],
            customdata=mapdata["Name"],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=mapdata['CumulativeByDorm'],
                color = mapdata['colors'], opacity=0.8
            ),
            hovertemplate = '<br><b>%{customdata} </b><br>' + "Total Cases: %{marker.size:,}",
            name = '',
    ))
    # Resize the circles
    sgmap.update_traces(
        mode='markers',
        marker={'sizemode':'area',
                'sizeref':0.2})
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
    return sgmap


def getcaseschart(data):
    chartdata = data[data['IsDorm']=='y'].groupby(['RowId','Id','Date','IsDorm'])['Cluster'].first().reset_index()
    nbcases = chartdata[['Date']].groupby(['Date']).size().reset_index(name='NewCases')
    nbcases['CumulativeByDorm'] = nbcases['NewCases'].cumsum()
    nbcases['tooltip'] = [x.strftime("%d %b") for x in nbcases['Date']]
    
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
    
    return chart1

def getwpcasesbarchart(data):
    # Work Pass Numbers
    wpdata = data[data['Permit']=='Work Permit holder'].groupby(['RowId','Id','Date','IsDorm','Permit'])['Cluster'].first().reset_index()
    nbwpass = wpdata[['Date','IsDorm']].groupby(['Date','IsDorm']).size().reset_index(name='NewCases')
    nbwpass['CumulativeByDorm'] = nbwpass.groupby(['Date','IsDorm']).sum().groupby(level=1).cumsum()['NewCases'].tolist()
    nbwpass['tooltip'] = [x.strftime("%d %b") for x in nbwpass['Date']]
    # Initialize figure
    chart3 = go.Figure()
    # Line chart
    chart3.add_trace(
        go.Bar(
            x=nbwpass['Date'][nbwpass['IsDorm']=='y'],
            y=nbwpass['CumulativeByDorm'][nbwpass['IsDorm']=='y'],
            marker_color = 'mistyrose',
            name='Total cases in Dorms',
            hovertemplate = '%{y}',
    ))
    chart3.add_trace(
        go.Bar(
            x=nbwpass['Date'][nbwpass['IsDorm']=='n'],
            y=nbwpass['CumulativeByDorm'][nbwpass['IsDorm']=='n'],
            marker_color = 'rebeccapurple',
            name='Total cases outside Dorms',
            hovertemplate = '%{y}',
    ))
    chart3.update_layout(
        title_text="Number of work pass cases over time",
        height=500,
        width=900,
        template="plotly_white",
        hovermode='x unified',
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_fixedrange=True,
        yaxis_fixedrange=True,
        barmode='stack',
    )
    chart3.update_xaxes(tickangle=-45,
                    tickmode='linear',
                    ticks="outside",
                   showline=True,
                   rangemode="tozero")
    chart3.update_yaxes(ticks="outside",
                   showline=True,
                    rangemode="tozero")
    return chart3


def getdormcaseschart(transdata):
    # # Area chart in plotly
    from bokeh.palettes import magma
    acol = magma(transdata.drop(['Date','tooltip'], axis = 1).shape[1])[::-1]
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
        height=500,
        width=1150,
        template="plotly_white",
        hovermode='x unified',
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        margin = {'b':0},
    )       
    chart2.update_xaxes(tickangle=-45,
                    tickmode='linear',
                    ticks="outside",
                   showline=True,
                   rangemode="tozero")
    chart2.update_yaxes(ticks="outside",
                   showline=True,
                    rangemode="tozero")
    
    return chart2



def getdatatable(transdata):
    # Table
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
        width=1800,
        height=900,
        margin=dict(
            l=1,
            r=1,
            pad=4
        ),
    )
    return tab
