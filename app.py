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

# Define the condition dropdown component
condition_dropdown = dcc.Dropdown(
    id='condition-dropdown',
    options=[
        {'label': 'Soleado', 'value': 'Soleado'},
        {'label': 'Lluvioso', 'value': 'Lluvioso'},
        {'label': 'Nublado', 'value': 'Nublado'},
        {'label': 'Helada', 'value': 'Helada'}
    ],
    placeholder="Selecciona alguna opción",  # This will be shown when no option is selected
    clearable=False,  # Prevents the user from clearing the selection, ensuring a value is always selected
    searchable=False  # Optional: makes the dropdown not searchable, simplifying the UI
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
    html.Div(id='upload-timestamp', style={'display': 'none'}),
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
        text_columns = ['Año', 'Mes', 'Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada', 'ID']
        for col in text_columns:
            df[col] = df[col].astype(str)
        
        # Filter the DataFrame to include relevant columns
        relevant_columns = ['Año', 'Mes', 'Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada', 'Fecha', 'ID']
        df_filtered = df[relevant_columns]

        # Use inspect to check if the table exists in the database
        inspector = inspect(engine)
        table_exists = inspector.has_table('table_clima4')

        if table_exists:
            existing_ids = pd.read_sql_table('table_clima4', engine, columns=['ID'])['ID'].tolist()
            df_filtered = df_filtered[~df_filtered['ID'].isin(existing_ids)]

        if not df_filtered.empty:
            df_filtered.to_sql('table_clima4', engine, if_exists='append', index=False)
            upload_timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            return html.Div(f"El archivo {filename} se ha subido correctamente."), upload_timestamp
        else:
            return html.Div(f"No se encontraron registros nuevos en el archivo {filename} para agregar."), ""
    return html.Div("Si desea subir un archivo, debe ingresar usuario y contraseña."), ""

@app.callback(
    Output('year-dropdown', 'options'),
    Input('upload-timestamp', 'children')  # Triggered after a file upload or any action that updates the timestamp
)
def update_year_dropdown(_):
    with engine.connect() as conn:
        query = "SELECT DISTINCT \"Año\" FROM table_clima4 WHERE \"Año\" IS NOT NULL ORDER BY \"Año\""
        df = pd.read_sql(query, conn)
    
    valid_years = df['Año'].dropna().unique().tolist()
    
    options = [{'label': int(year), 'value': int(year)} for year in valid_years if year is not None]
    
    return options


@app.callback(
    Output('month-dropdown', 'options'),
    [Input('year-dropdown', 'value')]
)
def update_month_dropdown(selected_year):
    if selected_year is not None:
        with engine.connect() as conn:
            query = f"""
            SELECT DISTINCT "Mes" 
            FROM table_clima4 
            WHERE "Año" = '{selected_year}' 
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
     Input('year-dropdown', 'value')]
)
def update_graph(selected_month, selected_year):
    if not selected_month or not selected_year:
        return html.Div("Seleccione un mes y un año para ver los gráficos.", style={'margin-top': '20px'})
    
    with engine.connect() as conn:
        query = f"""
        SELECT "Soleado", "Granizada", "Lluvioso", "Nublado", "Helada"
        FROM table_clima4
        WHERE "Mes" = '{selected_month}' AND "Año" = '{selected_year}';
        """
        df = pd.read_sql(query, conn)

    df = df.replace({None: pd.NA})
    
    responses = ['Poco', 'Normal', 'Mucho']
    conditions = ['Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada']
    plot_data = []

    for condition in conditions:
        condition_data = df[condition].dropna().value_counts().reindex(responses, fill_value=0).reset_index()
        condition_data.columns = ['Response', 'Frequency']
        condition_data['Condition'] = condition
        plot_data.append(condition_data)
    
    plot_df = pd.concat(plot_data, ignore_index=True)
    fig = px.bar(plot_df, x='Condition', y='Frequency', color='Response', barmode='group', title=f"Frecuencia de Condiciones Climáticas para {selected_month}")

    return dcc.Graph(figure=fig)


@app.callback(
    Output('evolution-graph', 'figure'),
    [Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('condition-dropdown', 'value'), 
     Input('upload-timestamp', 'children')]
)
def update_evolution_graph(selected_month, selected_year, selected_condition, _):
    
      # Return an empty graph if month, year, or condition is not selected
    if not selected_month or not selected_year or not selected_condition:
        return go.Figure()

    
    # Connect to the database and execute the query
    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima4
        WHERE "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
        ORDER BY "Fecha" ASC
        """
        df = pd.read_sql(query, conn)
    
    # Convert 'Fecha' to datetime and map responses to numerical values
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    response_mapping = {'Poco': 1, 'Normal': 2, 'Mucho': 3}
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Helada']:
        df[condition] = df[condition].map(response_mapping)

    # Filter the DataFrame based on the selected condition and calculate the daily average
    df = df.groupby('Fecha')[selected_condition].mean().reset_index()
    df.rename(columns={selected_condition: 'Response'}, inplace=True)

    # Create a new figure
    fig = go.Figure()

    # Add the line trace to the figure
    fig.add_trace(go.Scatter(
        x=df['Fecha'],
        y=df['Response'],
        mode='lines+markers',
        marker=dict(size=10),
        name=selected_condition
    ))

    # Update the layout of the figure
    fig.update_layout(
        title=f'Condiciones Climáticas Diarias para: {selected_condition}',
        xaxis_title='Fecha',
        yaxis_title='Índice'
    )

    return fig



# This might need to be adjusted according to the server's settings or environment.
try:
    locale.setlocale(locale.LC_TIME, 'es_ES')
except locale.Error:
    try:
        # Try a different locale known to be available
        locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
    except locale.Error:
        # Fallback to the default locale
        locale.setlocale(locale.LC_TIME, '')



@app.callback(
    Output('condition-days-table', 'children'),
    [Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),  # Nuevo input para el año seleccionado
     Input('upload-timestamp', 'children')]
)
def update_condition_days(selected_month, selected_year, _):
    if not selected_month or not selected_year:
        return ""
    
    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Helada"
        FROM table_clima4
        WHERE "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
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

if __name__ == '__main__':
    app.run_server(debug=True)

