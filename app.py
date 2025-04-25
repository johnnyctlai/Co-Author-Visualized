#!/usr/bin/env python
# coding: utf-8

# In[29]:



import pandas as pd
import numpy as np
import math 
import openpyxl
import plotly.express as px
import plotly


import dash
from dash import Dash, html, dcc, Input, Output, State, callback, Patch
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.graph_objects as go




# In[31]:


co_author_list = pd.read_excel('scopus_co_author.xlsx')
researcher = pd.read_excel('researcher_info.xlsx')



# In[33]:


co_author_list['Co-author'] = co_author_list.apply(
    lambda x: '[{}]'.format(x['Co-author']) + '({})'.format(x.hyperlink_author.split('&')[0]) 
    if type(x.hyperlink_author) == str else x['Co-author'], axis = 1)

co_author_list['Affiliation'] = co_author_list.apply(
    lambda x: '[{}]'.format(x['Affiliation']) + '({})'.format(x.hyperlink_aff.split('&')[0])
    if type(x.hyperlink_aff) == str else x['Affiliation'], axis = 1)






# In[36]:


researcher['Name'] = '[' + researcher.name + ']' + '(' + researcher['Scopus link'] + ')'
researcher['researcher_id'] = list(researcher.index)
co_author_list = co_author_list.merge(researcher[['name', 'Name', 'researcher_id']], left_on= 'Researcher', right_on = 'name', how = 'left')







# In[40]:


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

researcher_data = researcher[['Name', 'City', 'Domain', 'Panel', 'Number of co-authors','researcher_id']].dropna().sort_values('Name')
co_author_list = co_author_list[['Researcher', 'Co-author', 'Affiliation', 'City', 'Country/Territory',
                                'Name', 'city_lat', 'city_lon', 'Documents','researcher_id']]

researcher_selection = dag.AgGrid(
    id="select_researcher",
    rowData= researcher_data.to_dict('records'),
    columnDefs= [{"field": 'Name', "cellRenderer": "markdown", "linkTarget": "_blank", "initialWidth": 50},
                 {"field": 'City', "initialWidth": 30},
                 {"field": 'Domain', "initialWidth": 50},
                 {"field": 'Panel', "initialWidth": 100}],
    defaultColDef={"filter": True,  
                   "wrapHeaderText": True, 
                   "autoHeaderHeight": True, 
                   "initialWidth": 200 , 
                   "floatingFilter": False},
    dashGridOptions={"rowSelection": 'multiple'},
    selectedRows = [researcher_data.to_dict('records')[0]],
    columnSize="sizeToFit",
    rowClassRules = {"bg-secondary text-dark bg-opacity-25": "params.node.rowPinned === 'top' | params.node.rowPinned === 'bottom'"},
    style={"height": 400, "width": "100%"}
    )

control_panel = researcher_selection

heading = html.H1("Co-author Visualized",className="bg-secondary text-white p-2 mb-4")
intro = dcc.Markdown("""
    Visualize the co-authors locations of ERC grant receivers and highly cited researchers from Naples and Bologna [[GitHub]](https://github.com/johnnyctlai/Co-Author-Visualized)
    """)

researcher_selection_heading = html.H5("Select researcher(s) in the table below", 
                                       id = 'researcher_selection_heading',
                                       className="bg-secondary text-white p-2 mb-4")

researcher_selection_text = dcc.Markdown("""
    Hold down CTRL while clicking on the rows to select multiple reserchers.\n
    Hold down SHIFT while clicking a second row will select the range between the first and second row."
    """)

map_heading = html.H5("Map", 
                      id = 'map_heading',
                      className="bg-secondary text-white p-2 mb-4")

coauthor_list_heading = html.H5("Co-author List", 
                                id = 'coauthor_list_heading',
                                className="bg-secondary text-white p-2 mb-4")



table_cols = ['Researcher', 'Co-author', 'Affiliation', 'City', 'Country/Territory']

#data_filtered = data


grid = dag.AgGrid(
    id="grid",
    rowData= [],
    columnDefs= 
    [{"field": 'Researcher', "floatingFilter": False},
     {"field": 'Co-author', "cellRenderer": "markdown", "linkTarget": "_blank", "floatingFilter": False},
     {"field": 'Affiliation', "cellRenderer": "markdown", "linkTarget": "_blank", 
      "floatingFilter": False, "initialWidth": 250},
     {"field": 'Documents'}] +
    [{"field": c, "floatingFilter": False} for c in ['City', 'Country/Territory']],
    defaultColDef={"filter": True,  "wrapHeaderText": True, "autoHeaderHeight": True, "initialWidth": 100 },
    dashGridOptions={},
    columnSize="sizeToFit",
    #filterModel={'Report Year': {'filterType': 'number', 'type': 'equals', 'filter': 2023}},
    rowClassRules = {"bg-secondary text-dark bg-opacity-25": "params.node.rowPinned === 'top' | params.node.rowPinned === 'bottom'"},
    style={"height": 600, "width": "100%"}
    )



map_plot = dcc.Graph(id='co_author_map')

app.layout = dbc.Container(
    [dcc.Store(id="store-selected", data=[]),
     heading, intro,
     dbc.Row([dbc.Col(html.Div([researcher_selection_heading, researcher_selection_text, control_panel])),
              dbc.Col(html.Div([map_heading, dcc.Loading(map_plot, id = 'map_loading', type="circle")]))]),
     
     dbc.Row([coauthor_list_heading, dcc.Loading(grid, id = 'table_loading', type="circle")]),
              
         dbc.Col(
                [
                    dcc.Markdown(id="title")#,
                    #dbc.Row([dbc.Col(html.Div(id="paygap-card")), dbc.Col( html.Div(id="bonusgap-card"))]),
                    #html.Div(id="bar-chart-card", className="mt-4"),
                ],  md=9
            ),
        ], fluid=True)
       

@callback(Output("store-selected", "data"), Input("select_researcher", "selectedRows"))
def filter_coautor(researcher_selected):
    researcher_selected = [i['researcher_id'] for i in researcher_selected]
    dff = co_author_list[co_author_list['researcher_id'].isin(researcher_selected)]
    return dff.to_dict('records')



@callback(Output("co_author_map", "figure"), Input("store-selected", "data"), prevent_initial_call=True)
def co_author_map(records):
    passed_data = pd.DataFrame(records)
    group_by_cols = ['Country/Territory', 'City', 'city_lat', 'city_lon']

    map_data = passed_data.groupby(group_by_cols)['Co-author'].count().reset_index()#.sort_values('Co-author')

    fig = px.scatter_geo(map_data, lat = 'city_lat', lon = 'city_lon',
                         color='Country/Territory',
                         hover_name='City', 
                         size='Co-author',
                         #custom_data  = "linked_author",
                         scope = 'world',
                         projection="natural earth",
                         width = 700,
                         height = 500
                         )
    fig.update_layout(title_text = "Number of Co-authors" )
    fig.update_layout(showlegend=False)
    
    return fig

@callback(Output("map_heading", "children"), Input("select_researcher", "selectedRows"))
def update_map_title(researcher_selected):
    number_selected = len(researcher_selected)
    if number_selected <= 3:
        researcher_selected = [i['Name'].split(']')[0][1:] for i in researcher_selected]
        return 'Co-author Map by City - {}'.format(' ,'.join(researcher_selected))
    else:
        return 'Co-author Map by City - {} Seleted Researchers'.format(number_selected)


@callback(Output("grid", "rowData"), Input("store-selected", "data"), prevent_initial_call=True)
def update_rowdata(records):
    return records

@callback(Output("coauthor_list_heading", "children"), 
          Input("select_researcher", "selectedRows"),
          Input("store-selected", "data"))
def update_co_author_list_title(researcher_selected, co_author_filtered):
    researcher_selected = [i['Name'] for i in researcher_selected]#.split(']')[0][1:]
    displayed_number = len(co_author_filtered)
    total_co_author = researcher[researcher.Name.isin(researcher_selected)]['Number of co-authors'].sum()
    number_selected = len(researcher_selected)
    if number_selected <= 5:
        text = ' ,'.join([i.split(']')[0][1:] for i in researcher_selected])
    else:
        text = '{} Selected Researcher'.format(number_selected)
    
    return "Co-author List of {} ({} out of {})".format(text, 
                                                       displayed_number, 
                                                       int(total_co_author))


if __name__ == "__main__":
    app.run(debug=True)






