import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
from sqlalchemy import create_engine
import plotly.express as px
from sqlalchemy import inspect
import plotly.graph_objs as go
import locale
import dash_auth
import time

# Initialize your Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

condition_dropdown = dcc.Dropdown(
    id='condition-dropdown',
    options=[
        {'label': 'Todas', 'value': 'Todas'},  
        {'label': 'Soleado', 'value': 'Soleado'},
        {'label': 'Lluvioso', 'value': 'Lluvioso'},
        {'label': 'Nublado', 'value': 'Nublado'},
        {'label': 'Helada', 'value': 'Helada'}
    ],
    placeholder="Selecciona alguna opción",
    clearable=False,
    searchable=False
)



# Layout setup
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Visualizador de Observaciones Climáticas", 
                             style={'text-align': 'center', 
                                    'margin': '50px 0', 
                                    'font-family': '"Century Gothic", Arial, sans-serif', 
                                    'color': '#007bff', 
                                    'fontWeight': 'bold'}),
                             className="mb-4")),
    dcc.Store(id='login-state', data=False), 
    dbc.Row(dbc.Col(dcc.Dropdown(
    id='comunidad-dropdown',
    placeholder="Seleccione una comunidad",
    style={'width': '100%'}
    )), className="mb-3"),
    dbc.Row(dbc.Col(dcc.Dropdown(
    id='year-dropdown',
    placeholder="Seleccione un año",
    style={'width': '100%'} 
    )), className="mb-3"),  
    dbc.Row(dbc.Col(dcc.Dropdown(
    id='month-dropdown',
    placeholder="Seleccione un mes",
    style={'width': '100%'} 
    ))),  

    dbc.Row(dbc.Col(html.Div(id='weather-condition-frequency'), className="mb-3")),
    html.Div([
    html.Label('Selecciona alguna opción:', style={'margin-bottom': '15px'}),
    condition_dropdown,
    ]),
    dcc.Loading(id='loading-div', children=[dcc.Graph(id='evolution-graph')]),
    html.Div(id='condition-days-table'),
    dcc.Loading(id='loading-div2', children=[dcc.Graph(id='condition-average-graph')]),
    html.Div(id='upload-timestamp', style={'display': 'none'}),
    html.Div([
    html.Button('Login', id='login-button', n_clicks=0, style={
    'background-color': '#007BFF',  
    'color': 'white',  
    'border': 'none',  
    'padding': '10px 20px',  
    'text-align': 'center',  
    'text-decoration': 'none', 
    'display': 'inline-block',
    'font-size': '16px',
    'margin': '4px 2px',
    'cursor': 'pointer'
}),
    html.Div(style={'height': '10px'}),  
    html.Div([
        dcc.Input(id='username', type='text', placeholder='Usuario', style={'margin-right': '10px'}),
        dcc.Input(id='password', type='password', placeholder='Contraseña', style={'margin-right': '10px'}),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], id='login-form', style={'display': 'none', 'text-align': 'center'}),
], style={'text-align': 'center'}),
    dbc.Row(dbc.Col(dcc.Upload(
        id='upload-data',
        children=html.Div(['Arrastre aquí o ', html.A('Seleccione Archivos')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px',
            'display': 'none'  # Add this line
        },
        multiple=False, accept='.xlsx'
    )), className="mb-3"),
    dbc.Row(dbc.Col(dcc.Loading(
        id="loading-upload",
        children=[html.Div(id='output-data-upload')],
        type="default",
    )), className="mb-3"),
], fluid=True, style={'padding': '20px'})


# Database connection setup
DATABASE_URL = "postgresql://cesder_user:GEtjvJf0VGG8mpa4AU7PF74eMEXef3q4@dpg-cnfn9q6g1b2c73bakt30-a.oregon-postgres.render.com/cesder"
engine = create_engine(DATABASE_URL)

@app.callback(
    [Output('output-data-upload', 'children'),
     Output('upload-timestamp', 'children')], 
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def handle_file_upload(contents, filename):
    if contents is not None:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        excel_file = io.BytesIO(decoded)
        df = pd.read_excel(excel_file, engine='openpyxl')

        # Rename columns as specified
        df.rename(columns={
            'Indique su comunidad': 'Comunidad',
            'Indique el mes del registro': 'Mes',
            'Indique_el_estado_de_empo_y_su_intensidad/Soleado': 'Soleado',
            'Indique_el_estado_de_empo_y_su_intensidad/Granizada': 'Granizada',
            'Indique_el_estado_de_empo_y_su_intensidad/Lluvioso': 'Lluvioso',
            'Indique_el_estado_de_empo_y_su_intensidad/Nublado': 'Nublado',
            'Indique_el_estado_de_empo_y_su_intensidad/Helada': 'Helada',
            'Indique la fecha del registro': 'Fecha',  # New column
            '_id': 'ID'  # Unique ID column
        }, inplace=True)

        # Ensure the 'Fecha' column is in the correct date format
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y-%m-%d')
        

        # Convert all relevant columns to string to ensure TEXT data type in SQL
        text_columns = ['Comunidad', 'Año', 'Mes', 'Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada', 'ID']
        for col in text_columns:
            df[col] = df[col].astype(str)
        
        # Filter the DataFrame to include relevant columns
        relevant_columns = ['Comunidad', 'Año', 'Mes', 'Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada', 'Fecha', 'ID']
        df_filtered = df[relevant_columns]

        # Use inspect to check if the table exists in the database
        inspector = inspect(engine)
        table_exists = inspector.has_table('table_clima5')

        if table_exists:
            existing_ids = pd.read_sql_table('table_clima5', engine, columns=['ID'])['ID'].tolist()
            df_filtered = df_filtered[~df_filtered['ID'].isin(existing_ids)]

        if not df_filtered.empty:
            df_filtered.to_sql('table_clima5', engine, if_exists='append', index=False)
            upload_timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            return html.Div(f"El archivo {filename} se ha subido correctamente."), upload_timestamp
        else:
            return html.Div(f"No se encontraron registros nuevos en el archivo {filename} para agregar."), ""
    return html.Div("Si desea subir un archivo, debe ingresar usuario y contraseña."), ""


@app.callback(
    Output('comunidad-dropdown', 'options'),
    Input('upload-timestamp', 'children') 
)
def update_comunidad_dropdown(_):
    with engine.connect() as conn:
        # Ensure column names are case-sensitive by using double quotes if the actual column name in the database is mixed-case.
        # Adjust "Comunidad" to match the exact case used in your database table.
        df = pd.read_sql('SELECT DISTINCT "Comunidad" FROM table_clima5 ORDER BY "Comunidad"', conn)
    options = [{'label': comunidad, 'value': comunidad} for comunidad in df['Comunidad'].dropna().tolist()]
    return options



@app.callback(
    Output('year-dropdown', 'options'),
    [Input('comunidad-dropdown', 'value'),  # New input
     Input('upload-timestamp', 'children')]
)
def update_year_dropdown(selected_comunidad, _):
    if selected_comunidad:
        with engine.connect() as conn:
            query = f"""
            SELECT DISTINCT "Año" FROM table_clima5
            WHERE "Comunidad" = '{selected_comunidad}'
            ORDER BY "Año";
            """
            df = pd.read_sql(query, conn)
    else:
        df = pd.DataFrame(columns=['Año'])  # Fallback to an empty DataFrame if no community is selected
    
    options = [{'label': int(year), 'value': int(year)} for year in df['Año'].dropna().unique().tolist()]
    return options


@app.callback(
    Output('month-dropdown', 'options'),
    [Input('comunidad-dropdown', 'value'),  # New input for community
     Input('year-dropdown', 'value')]
)
def update_month_dropdown(selected_comunidad, selected_year):
    if selected_year is not None and selected_comunidad is not None:
        with engine.connect() as conn:
            query = f"""
            SELECT DISTINCT "Mes" 
            FROM table_clima5 
            WHERE "Año" = '{selected_year}' AND "Comunidad" = '{selected_comunidad}'
            ORDER BY "Mes";
            """
            df = pd.read_sql(query, conn)
        
        valid_months = df['Mes'].dropna().unique().tolist()
        options = [{'label': month, 'value': month} for month in valid_months if month is not None]
    else:
        options = []

    return options



@app.callback(
    Output('weather-condition-frequency', 'children'),
    [Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('comunidad-dropdown', 'value'),  # Included comunidad-dropdown as a new input
     Input('upload-timestamp', 'children')]
)
def update_graph(selected_month, selected_year, selected_comunidad, _):
    if not selected_month or not selected_year or not selected_comunidad:  # Check if comunidad is also selected
        return html.Div("Seleccione una comunidad, un mes y un año para ver los gráficos.", style={'margin-top': '20px'})
    
    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima5  
        WHERE "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Comunidad" = '{selected_comunidad}';
        """
        df = pd.read_sql(query, conn)

    # Replace None with pd.NA (pandas NA)
    df = df.replace({None: pd.NA})
    
    # Function to determine the majority vote for each day
    def majority_vote(s):
        if s.dropna().empty:
            return pd.NA
        return s.mode()[0] if not s.mode().empty else pd.NA

    # Calculate the majority response for each condition per day
    majority_responses = df.groupby('Fecha').agg({condition: majority_vote for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']})
    
    plot_data = []

    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        condition_data = majority_responses[condition].value_counts().reset_index()
        condition_data.columns = ['Response', 'Days']
        condition_data['Condition'] = condition
        plot_data.append(condition_data)
    
    plot_df = pd.concat(plot_data, ignore_index=True)

    # Explicitly filter out 'nan' strings from the 'Response' column
    plot_df = plot_df[plot_df['Response'].astype(str).str.lower() != 'nan']

    fig = px.bar(plot_df, x='Condition', y='Days', color='Response', barmode='group', 
                 title=f"Días por Condición Climática para {selected_month}/{selected_year}",
                 labels={"Days": "Número de Días", "Condition": "Condición Climática", "Response": "Respuesta Mayoritaria"})
    
    return dcc.Graph(figure=fig)



from pandas import to_numeric


@app.callback(
    Output('evolution-graph', 'figure'),
    [Input('comunidad-dropdown', 'value'),  # Add comunidad-dropdown as an input
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('condition-dropdown', 'value'), 
     Input('upload-timestamp', 'children')]
)
def update_evolution_graph(selected_comunidad, selected_month, selected_year, selected_condition, _):
    # Return an empty graph if month, year, or condition is not selected
    if not selected_comunidad or not selected_month or not selected_year or selected_condition is None:
        return go.Figure()

    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima5  
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
        ORDER BY "Fecha" ASC;
        """
        df = pd.read_sql(query, conn)
    
    # Convert 'Fecha' to datetime and map responses to numerical values
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    response_mapping = {'Poco': 1, 'Normal': 2, 'Mucho': 3}
    df = df.replace(response_mapping)

    # Convert relevant columns to numeric, ensuring non-convertible values become NaN
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        df[condition] = pd.to_numeric(df[condition], errors='coerce')

    # Create a new figure
    fig = go.Figure()

    if selected_condition == "Todas":
        # Plot each condition as a separate line
        for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
            temp_df = df.groupby('Fecha')[condition].agg(['mean', 'count']).reset_index()
            temp_df.rename(columns={'mean': 'Response', 'count': 'Count'}, inplace=True)
            
            # Add the line trace to the figure for each condition
            fig.add_trace(go.Scatter(
                x=temp_df['Fecha'],
                y=temp_df['Response'],
                mode='lines+markers',
                marker=dict(size=10),
                name=condition,
                hovertemplate=
                '<b>Fecha</b>: %{x}<br>' +
                '<b>Índice</b>: %{y}<br>' +
                '<b>Número de Informantes</b>: %{text}',
                text=temp_df['Count']
            ))
    else:
        # Handle plotting for a single selected condition
        temp_df = df.groupby('Fecha')[selected_condition].agg(['mean', 'count']).reset_index()
        temp_df.rename(columns={'mean': 'Response', 'count': 'Count'}, inplace=True)
        
        # Add the line trace to the figure for the selected condition
        fig.add_trace(go.Scatter(
            x=temp_df['Fecha'],
            y=temp_df['Response'],
            mode='lines+markers',
            marker=dict(size=10),
            name=selected_condition,
            hovertemplate=
            '<b>Fecha</b>: %{x}<br>' +
            '<b>Índice</b>: %{y}<br>' +
            '<b>Número de Informantes</b>: %{text}',
            text=temp_df['Count']
        ))

    # Update the layout of the figure
    fig.update_layout(
        title=f'Condiciones Climáticas Diarias para: {selected_month}/{selected_year}',
        xaxis_title='Fecha',
        yaxis_title='Índice',
        legend_title="Condición"
    )

    return fig

# This might need to be adjusted according to the server's settings or environment.
locale.setlocale(locale.LC_TIME, 'es_ES')



@app.callback(
    Output('condition-days-table', 'children'),
    [Input('comunidad-dropdown', 'value'),  # Add comunidad-dropdown as an input
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),  
     Input('upload-timestamp', 'children')]
)
def update_condition_days(selected_comunidad, selected_month, selected_year, _):
    if not selected_comunidad or not selected_month or not selected_year:
        return ""
    
    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima5  
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
        """
        df = pd.read_sql(query, conn)

    # Convert 'Fecha' to datetime to ensure proper handling
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    

    # Map the string responses to numeric values
    response_mapping = {'Poco': 1, 'Normal': 2, 'Mucho': 3}
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        df[condition] = df[condition].map(response_mapping)

    # Compute the averages
    df = df.groupby('Fecha').mean().reset_index()

    # Filter based on the standardized threshold of 2
    condition_days = {}
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        # Here we extract the day of the week and the day of the month
        condition_days[condition] = df[df[condition] > 2]['Fecha'].apply(lambda x: x.strftime('%A %d')).apply(str.capitalize).tolist()

    # Prepare the display content
    children = [html.H4(f"{selected_month} - Días con condiciones específicas superando el umbral de 2 (Normal)", 
                    style={
                        'margin-bottom': '30px', 
                        'margin-left': '70px', 
                        'font-size': '19px', 
                        'font-weight': 'normal'
                    })]
    # Find the maximum length of the lists in condition_days
    max_length = max(len(v) for v in condition_days.values())

    # Pad shorter lists with None
    for condition in condition_days:
        condition_days[condition] += [None] * (max_length - len(condition_days[condition]))

    # Create a DataFrame for the table
    table_df = pd.DataFrame(condition_days)
    
    # Create the DataTable
    table = dash_table.DataTable(
        data=table_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in table_df.columns],
        style_cell={
            'textAlign': 'left',
            'minWidth': '70px', # min width of each column.
            'width': '70px', # width of each column.
            'maxWidth': '90px', # max width of each column.
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        }
    )

    # Wrap the table in a Div and set the width
    table_container = html.Div(
        children=[table],
        style={'width': '90%', 'margin': '0 auto'}  # Adjust the width as needed
    )

    children.append(table_container)

    return html.Div(children)

@app.callback(
    Output('upload-data', 'style'),
    Input('login-state', 'data')
)
def update_upload_visibility(is_logged_in):
    if is_logged_in:
        return {
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px'
        }
    else:
        return {
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px',
            'display': 'none'
        }
    
@app.callback(
    Output('login-form', 'style'),
    [Input('login-button', 'n_clicks')]
)
def display_login_form(n):
    if n > 0:
        return {'display': 'block'}
    return {'display': 'none'}

@app.callback(
    Output('login-state', 'data'),
    [Input('submit-button', 'n_clicks')],
    [State('username', 'value'), State('password', 'value')]
)
def login(n, username, password):
    if n > 0:
        if username == "admin" and password == "password":
            return True
    return False

@app.callback(
    Output('condition-average-graph', 'figure'),  # Ensure you have added a dcc.Graph with this ID in your layout
    [Input('comunidad-dropdown', 'value'),  # Add comunidad-dropdown as an input
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children')]
)
def update_condition_average_graph(selected_comunidad, selected_year, _):
    if selected_year is None or selected_comunidad is None:
        return go.Figure()  # Return an empty graph if no year or community is selected

    with engine.connect() as conn:
        # Update query to fetch data for the selected year and community
        query = f"""
        SELECT "Mes", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima5 
        WHERE "Año" = '{selected_year}' AND "Comunidad" = '{selected_comunidad}';
        """
        df = pd.read_sql(query, conn)

    # Map string responses to numeric values, ignoring NaNs
    response_mapping = {'Poco': 1, 'Normal': 2, 'Mucho': 3}
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        df[condition] = df[condition].map(response_mapping)

    # Compute the average for each condition per month, ignoring NaNs in the calculation
    monthly_averages = df.groupby('Mes')[['Soleado', 'Lluvioso', 'Nublado', 'Helada']].mean().reset_index()
    
    # Dynamically set the month order based on the available data
    full_month_order = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    available_months = monthly_averages['Mes'].unique().tolist()
    month_order = [month for month in full_month_order if month in available_months]
    
    # Melt the dataframe to make it suitable for a bar graph with plotly
    melted_df = monthly_averages.melt(id_vars=['Mes'], var_name='Condition', value_name='Average')

    # Ensure the 'Mes' column in melted_df is ordered correctly based on month_order
    melted_df['Mes'] = pd.Categorical(melted_df['Mes'], categories=month_order, ordered=True)

    # Generate the bar graph
    fig = px.bar(
        melted_df,
        x='Mes',
        y='Average',
        color='Condition',
        barmode='group',
        title=f'Promedio de Condiciones Climáticas por Mes en el Año {selected_year}',
        category_orders={"Mes": month_order}  # Ensures the x-axis follows the dynamic month order
    )
    
    # Adjust the title to reflect the inclusion of the selected community
    fig.update_layout(
        title=f'Promedio de Condiciones Climáticas por Mes para {selected_comunidad} en el Año {selected_year}',
        xaxis_title='Mes',
        yaxis_title='Promedio de Respuestas'
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)


