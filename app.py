# APP SERVER
import dash
import dash_core_components as dcc
import dash_html_components as html
from charts import *
from flask_caching import Cache


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

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})

TIMEOUT = 3600

@cache.memoize(timeout=TIMEOUT)
def serve_layout():
    print("running serve layout for data refresh")
    allcases = load_data_fromJSON()
    alldata = load_data_fromGsheet()
    data = source_data(allcases,alldata[0])    

    mapdata = getmapdata(data,alldata[1],alldata[2])
    transdata = gettransdata(data,alldata[1],alldata[2])

    mapchart = getmapchart(mapdata)
    caseschart = getcaseschart(data)
    wpchart = getwpcasesbarchart(data)
    dormschart = getdormcaseschart(transdata)
    tablechart = getdatatable(transdata)

    layout = html.Div(children=[
        html.H2(children='COVID19 - Migrant Worker Dorm Infections'),

        html.Div(children='''
            A dashboard to visualise the infections across foreign worker dormitories.
        '''),

        html.Div(className='container',
            children=[
            dcc.Graph(
                id='map-graph',
                className='map-component',
                figure=mapchart
            ),

            html.Div(className='chart-container',
            children=[
                dcc.Graph(
                id='cases-graph',
                className='chart-component',
                figure=caseschart
                ),

                html.P(className='usage-tip',
                children='For mobile usage: \nTap anywhere on the chart to see details in a popover.\nSlide or pinch on chart to remove the popover.'),
            ]),

            dcc.Graph(
                id='dorm-area-graph',
                className='chart-component',
                figure=dormschart
            ),

            dcc.Graph(
                id='data-table',
                className='table-component',
                figure=tablechart
            ),

        ])

    ])

    return layout

app.layout = serve_layout

if __name__ == '__main__':
    app.run_server(debug=True)
