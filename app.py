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
from plotly.subplots import make_subplots
import numpy as np

# Initialize your Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

informant_dropdown = dcc.Dropdown(
    id='informant-dropdown',
    placeholder="Seleccione un informante",
    options=[{'label': 'Todos', 'value': 'Todos'}],
    value='Todos',
    style={'width': '100%'}
)

# Database connection setup
DATABASE_URL = "postgresql://cesder_test_2rz0_user:lPPzU1EjETv9U8TPUWQBl2S5SdIdSXoc@dpg-cq58mt6ehbks73bl3rbg-a.oregon-postgres.render.com/cesder_test_2rz0"
engine = create_engine(DATABASE_URL)


# Layout setup
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Pachagrama Digital", 
                             style={'text-align': 'center', 
                                    'margin': '50px 0', 
                                    'font-family': '"Century Gothic", Arial, sans-serif', 
                                    'color': '#007bff', 
                                    'fontWeight': 'bold'}),
                             className="mb-4")),
    dcc.Store(id='login-state', data=False), 
    html.Div(id='informant-ranking'),
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
    ), className="mb-3")),
    dbc.Row(dbc.Col(informant_dropdown), className="mb-3"),  

    dcc.Checklist(
        id='labors-toggle',
        options=[{'label': '  Mostrar Información sobre Maíz y Frijol', 'value': 'show'}],
        value=[],
        style={'margin-top': '20px', 'margin-bottom': '20px'}
    ),
      # Graphs and tables wrapped for visibility control
    dcc.Loading(id='loading-climate', children=[dcc.Graph(id='climate-conditions-graph')]),
    dcc.Loading(id='loading-labor', children=[dcc.Graph(id='labor-activities-graph')]),
    html.Div(id='graphs-container', children=[
        dcc.Loading(id='loading-div3', children=[html.Div(id='condition-days-table')]),
    ]),
    html.Div(id='maiz-risks-table'),
    html.Div(id='frijol-risks-table'),
    dcc.Graph(
    id='maiz-status-graph',
    style={'display': 'none'}  # Start as invisible
    ),

    dcc.Graph(
    id='frijol-status-graph',
    style={'display': 'none'}  # Start as invisible
    ),
    html.Div(id='climate-discrepancies-table'),
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

        # Identify all columns that start with 'Seleccione su nombre y apellido'
        name_columns = [col for col in df.columns if col.startswith('Seleccione su nombre y apellido')]

        # Rename columns as specified
        df.rename(columns={
            'Seleccione su comunidad': 'Comunidad',
            'Indique el mes de registro': 'Mes',
            'Indique el estado del clima y su intensidad': 'Estado del clima', 
            'Indique el estado del tiempo y su intensidad': 'Estado del tiempo', 
            'Soleado': 'Soleado',
            'Granizada': 'Granizada',
            'Lluvioso': 'Lluvioso',
            'Nublado': 'Nublado',
            'Helada': 'Helada',
            '¿Qué fase lunar corresponde a la noche de este día?': 'Fase lunar',
            'Podría contarnos cómo le va con el cultivo de maíz': 'Estado del maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz': 'Riesgos maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Granizada': 'Riesgo granizada-maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Helada': 'Riesgo helada-maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Sequía': 'Riesgo sequía-maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Golpe de calor': 'Riesgo golpe de calor-maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Inundación': 'Riesgo inundación-maíz',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de maíz/Plagas y enfermedades': 'Riesgo plagas y enfermedades-maíz',
            'Podría contarnos cómo le va con el cultivo de frijol': 'Estado del frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol': 'Riesgos frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Granizada': 'Riesgo granizada-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Helada': 'Riesgo helada-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Sequía': 'Riesgo sequía-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Golpe de calor': 'Riesgo golpe de calor-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Inundación': 'Riesgo inundación-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su cultivo de frijol/Plagas y enfermedades': 'Riesgo plagas y enfermedades-frijol',
            '¿Qué variedad de maíz siembra?': 'Variedad de maíz',
            '¿Qué variedad de maíz siembra?/Maíz blanco': 'Maíz blanco',
            '¿Qué variedad de maíz siembra?/Maíz azul': 'Maíz azul',
            '¿Qué variedad de maíz siembra?/Maíz amarillo': 'Maíz amarillo',
            '¿Qué labores agrícolas realizó hoy en el maíz?': 'Labores maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Labranza': 'Labranza-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Preparación': 'Preparación-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Fertilización': 'Fertilización-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Siembra': 'Siembra-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Aterrada': 'Aterrada-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Despunte': 'Despunte-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Cosecha': 'Cosecha-maíz',
            '¿Qué labores agrícolas realizó hoy en el maíz?/Ninguna de las anteriores': 'Ninguna-maíz',
            '¿Qué variedad de frijol siembra?': 'Variedad de frijol',
            '¿Qué variedad de frijol siembra?/Frijol negro': 'Frijol negro',
            '¿Qué variedad de frijol siembra?/Frijol amarillo': 'Frijol amarillo',
            '¿Qué variedad de frijol siembra?/Frijol enredador': 'Frijol enredador', 
            '¿Qué labores agrícolas realizó el día de hoy en el cultivo del frijol?': 'Labores frijol',
            '¿Qué labores agrícolas realizó hoy en el frijol?/Labranza': 'Labranza-frijol',
            '¿Qué labores agrícolas realizó hoy en el frijol?/Deshierba': 'Deshierba-frijol',
            '¿Qué labores agrícolas realizó hoy en el frijol?/Siembra': 'Siembra-frijol',
            '¿Qué labores agrícolas realizó hoy en el frijol?/Cosecha': 'Cosecha-frijol',
            '¿Qué labores agrícolas realizó hoy en el frijol?/Ninguna de las anteriores': 'Ninguna-frijol',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción': 'Riesgos producción',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Granizada': 'Riesgo granizada-producción',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Helada': 'Riesgo helada-producción', 
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Sequía': 'Riesgo sequía-producción',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Golpe de calor': 'Riesgo golpe de calor-producción',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Inundación': 'Riesgo inundación-producción',
            'Debido a cuál o cuáles de los siguientes riesgos le fue mal en su producción/Plagas y enfermedades': 'Riesgo plagas y enfermedades-producción',
            '_submission_time': 'Fecha3', 
            'Indique la fecha del registro': 'Fecha2',
            '_id': 'ID',
        }, inplace=True)

                # Convert 'Fecha3' to datetime format (YYYY-MM-DD)
        df['Fecha3'] = pd.to_datetime(df['Fecha3'], format='%m/%d/%Y %I:%M:%S %p')
        
        # Convert 'Fecha2' to datetime format (YYYY-MM-DD) and handle missing values
        df['Fecha2'] = pd.to_datetime(df['Fecha2'], format='%m/%d/%Y', errors='coerce')
        
        # Extract only the date part (year, month, day) from 'Fecha3'
        df['Fecha3'] = df['Fecha3'].dt.strftime('%Y-%m-%d')
        
        # Create 'Fecha' column using 'Fecha2' if available, otherwise use 'Fecha3'
        df['Fecha'] = df['Fecha2'].fillna(df['Fecha3'])
        
        # Convert 'Fecha' back to datetime to extract the year
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y-%m-%d')
        
        # Extract the year from the 'Fecha' column
        df['Año'] = df['Fecha'].dt.year

       
        # Merge the informant columns into a single "Informante" column
        df['Informante'] = df[name_columns].apply(lambda x: x.dropna().iloc[0] if x.notna().any() else pd.NA, axis=1)

        # Drop the original informant columns
        df.drop(columns=name_columns, inplace=True)

        # Convert all relevant columns to string to ensure TEXT data type in SQL
        text_columns = ['Comunidad', 'Año', 'Mes', 'Soleado', 'Granizada', 'Lluvioso', 'Nublado', 'Helada', 'ID',
                        'Riesgo granizada-maíz', 'Riesgo helada-maíz', 'Riesgo sequía-maíz', 'Riesgo golpe de calor-maíz',
                        'Riesgo inundación-maíz', 'Riesgo plagas y enfermedades-maíz', 'Riesgo granizada-frijol',
                        'Riesgo helada-frijol', 'Riesgo sequía-frijol', 'Riesgo golpe de calor-frijol', 'Riesgo inundación-frijol',
                        'Riesgo plagas y enfermedades-frijol', 'Labranza-maíz', 'Fertilización-maíz', 'Siembra-maíz',
                        'Aterrada-maíz', 'Despunte-maíz', 'Cosecha-maíz', 'Labranza-frijol', 'Deshierba-frijol',
                        'Siembra-frijol', 'Cosecha-frijol', 'Informante', 'Fase lunar', 'Estado del maíz', 'Estado del frijol', 'Preparación-maíz']
        for col in text_columns:
            df[col] = df[col].astype(str)

        # Use inspect to check if the table exists in the database
        inspector = inspect(engine)
        table_exists = inspector.has_table('table_clima28')

        if table_exists:
            existing_ids = pd.read_sql_table('table_clima28', engine, columns=['ID'])['ID'].tolist()
            df = df[~df['ID'].isin(existing_ids)]

        if not df.empty:
            df.to_sql('table_clima28', engine, if_exists='append', index=False)
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
        df = pd.read_sql('SELECT DISTINCT "Comunidad" FROM table_clima28 ORDER BY "Comunidad"', conn)
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
            SELECT DISTINCT "Año" FROM table_clima28
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
            FROM table_clima28 
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
    Output('informant-dropdown', 'options'),
    [Input('comunidad-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('upload-timestamp', 'children')]
)
def update_informant_dropdown(selected_comunidad, selected_year, selected_month, _):
    options = [{'label': 'Todos', 'value': 'Todos'}]  # Include 'Todos' as the default option
    if selected_comunidad and selected_year and selected_month:
        with engine.connect() as conn:
            query = f"""
            SELECT DISTINCT "Informante" FROM table_clima28
            WHERE "Comunidad" = '{selected_comunidad}' AND "Año" = '{selected_year}' AND "Mes" = '{selected_month}'
            ORDER BY "Informante";
            """
            df = pd.read_sql(query, conn)
        options.extend([{'label': informant, 'value': informant} for informant in df['Informante'].tolist()])
    return options



from pandas import to_numeric

@app.callback(
    Output('climate-conditions-graph', 'figure'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_climate_conditions_graph(selected_comunidad, selected_month, selected_year, _, selected_informant):
    if not selected_comunidad or not selected_month or not selected_year or not selected_informant:
        return go.Figure()

    with engine.connect() as conn:
        if selected_informant == 'Todos':
            query = f"""
            SELECT "Fecha", "Soleado", "Lluvioso", "Nublado"
            FROM table_clima28
            WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
            ORDER BY "Fecha" ASC;
            """
        else:
            query = f"""
            SELECT "Fecha", "Soleado", "Lluvioso", "Nublado"
            FROM table_clima28
            WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Informante" = '{selected_informant}'
            ORDER BY "Fecha" ASC;
            """
        df = pd.read_sql(query, conn)

        df['Fecha'] = pd.to_datetime(df['Fecha'])
        response_mapping = {'Nada': 0, 'Poco': 1, 'Normal': 2, 'Mucho': 3}
        df = df.replace(response_mapping)

        for condition in ['Soleado', 'Lluvioso', 'Nublado']:
            df[condition] = pd.to_numeric(df[condition], errors='coerce')

        df[['Soleado', 'Lluvioso', 'Nublado']] = df[['Soleado', 'Lluvioso', 'Nublado']].applymap(lambda x: 0 if pd.isna(x) else x)

        # Make nublado dot disappear when lluvioso > 0 and nublado = 0
        df.loc[(df['Lluvioso'] > 0) & (df['Nublado'] == 0), 'Nublado'] = np.nan

        date_range = pd.date_range(start=df['Fecha'].min(), end=df['Fecha'].max(), freq='D')

        condition_icons = {
            'Soleado': '☀️',
            'Lluvioso': '🌧',
            'Nublado': '☁️'
        }

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.33, 0.33, 0.33])

        for i, condition in enumerate(['Soleado', 'Lluvioso', 'Nublado']):
            temp_df = df.groupby('Fecha')[condition].agg(['mean', 'count']).reset_index()
            temp_df.rename(columns={'mean': 'Response', 'count': 'Count'}, inplace=True)

            informants_df = df.groupby('Fecha').size().reset_index(name='Informants')
            temp_df = pd.merge(temp_df, informants_df, on='Fecha', how='left')

            fig.add_trace(go.Scatter(
                x=temp_df['Fecha'],
                y=temp_df['Response'],
                mode='lines+markers',
                line=dict(width=4),
                marker=dict(size=12),
                name=condition,
                hovertemplate='<b>Fecha</b>: %{x}<br><b>Índice</b>: %{y}<br><b>Número de Informantes</b>: %{text}',
                text=temp_df['Informants']
            ), row=i+1, col=1)

            fig.update_yaxes(
                title=dict(text=condition_icons[condition], font=dict(size=50), standoff=0),
                title_standoff=20,
                range=[-0.2, 3.5],
                tickvals=[0, 1, 2, 3],
                ticktext=['Nada', 'Poco', 'Normal', 'Mucho'],
                row=i+1, col=1
            )

            fig.update_xaxes(
                tickmode='auto',
                nticks=10,
                tickangle=0,
                row=i+1, col=1
            )

        total_informants_query = f"""
        SELECT COUNT(DISTINCT "Informante") as total_informants
        FROM table_clima28
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}';
        """
        total_informants = pd.read_sql(total_informants_query, conn).iloc[0]['total_informants']

        response_percentage_df = df.groupby('Fecha').size().reset_index(name='num_responses')
        response_percentage_df['num_responses'] = response_percentage_df['num_responses'].fillna(0)
        response_percentage_df['percentage'] = response_percentage_df['num_responses'] / total_informants * 100

        def get_color(percentage, date):
            if date not in df['Fecha'].values:
                return 'rgba(255, 0, 0, 0.2)'  # Red for missing dates
            elif percentage == 0:
                return 'rgba(255, 0, 0, 0.2)'  # Red
            elif 0 < percentage < 25:
                return 'rgba(255, 165, 0, 0.2)'  # Orange
            elif 25 <= percentage < 75:
                return 'rgba(255, 255, 0, 0.2)'  # Yellow
            else:
                return 'rgba(0, 255, 0, 0.2)'  # Green

        for date in date_range:
            if date in response_percentage_df['Fecha'].values:
                percentage = response_percentage_df.loc[response_percentage_df['Fecha'] == date, 'percentage'].iloc[0]
            else:
                percentage = 0

            color = get_color(percentage, date)

            for i in range(3):
                fig.add_shape(
                    type='rect',
                    x0=date - pd.Timedelta(hours=12),
                    y0=0,
                    x1=date + pd.Timedelta(hours=12),
                    y1=4,
                    fillcolor=color,
                    layer='below',
                    line_width=0,
                    row=i+1,
                    col=1
                )

        fig.update_layout(
            height=600,
            title=dict(text=f'Condiciones Climáticas Diarias para: {selected_month}/{selected_year}', x=0.5),
            showlegend=True,
            margin=dict(l=100, r=50, t=90, b=90)
        )

        for i, condition in enumerate(['Soleado', 'Lluvioso', 'Nublado']):
            fig['layout'][f'yaxis{i+1}']['title']['text'] = f"<span style='margin-right: 20px; transform: rotate(90deg); display: inline-block;'>{condition_icons[condition]}</span>"

    return fig

@app.callback(
    Output('labor-activities-graph', 'figure'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_labor_activities_graph(selected_comunidad, selected_month, selected_year, _, selected_informant):
    if not selected_comunidad or not selected_month or not selected_year or not selected_informant:
        return go.Figure()

    with engine.connect() as conn:
        if selected_informant == 'Todos':
            query = f"""
                SELECT "Fecha", "Informante", 
                       "Preparación-maíz", "Labranza-maíz", "Fertilización-maíz", "Siembra-maíz", 
                       "Aterrada-maíz", "Despunte-maíz", "Cosecha-maíz",
                       "Labranza-frijol", "Deshierba-frijol", "Siembra-frijol", "Cosecha-frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
                ORDER BY "Fecha" ASC;
            """
        else:
            query = f"""
                SELECT "Fecha", "Informante", 
                       "Preparación-maíz", "Labranza-maíz", "Fertilización-maíz", "Siembra-maíz", 
                       "Aterrada-maíz", "Despunte-maíz", "Cosecha-maíz",
                       "Labranza-frijol", "Deshierba-frijol", "Siembra-frijol", "Cosecha-frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Informante" = '{selected_informant}'
                ORDER BY "Fecha" ASC;
            """
        
        df = pd.read_sql(query, conn)

        total_informants_query = f"""
        SELECT COUNT(DISTINCT "Informante") as total_informants
        FROM table_clima28
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}';
        """
        total_informants = pd.read_sql(total_informants_query, conn).iloc[0]['total_informants']

    df['Fecha'] = pd.to_datetime(df['Fecha'])

    maize_labors = ['Preparación-maíz', 'Labranza-maíz', 'Fertilización-maíz', 'Siembra-maíz', 'Aterrada-maíz', 'Despunte-maíz', 'Cosecha-maíz']
    beans_labors = ['Labranza-frijol', 'Deshierba-frijol', 'Siembra-frijol', 'Cosecha-frijol']

    for labor in maize_labors + beans_labors:
        df[labor] = df[labor].apply(lambda x: 1 if x == '1.0' else pd.NA)

    # Only display labors that are in the database
    maize_labors = [labor for labor in maize_labors if df[labor].notna().any()]
    beans_labors = [labor for labor in beans_labors if df[labor].notna().any()]

    maize_data = df.melt(id_vars=['Fecha', 'Informante'], value_vars=maize_labors, var_name='Labor', value_name='Realizó')
    maize_data = maize_data[maize_data['Realizó'].notna()]
    maize_data['Labor'] = maize_data['Labor'].str.replace('-maíz', '')

    beans_data = df.melt(id_vars=['Fecha', 'Informante'], value_vars=beans_labors, var_name='Labor', value_name='Realizó')
    beans_data = beans_data[beans_data['Realizó'].notna()]
    beans_data['Labor'] = beans_data['Labor'].str.replace('-frijol', '')

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.5, 0.5])

    date_range = pd.date_range(start=df['Fecha'].min(), end=df['Fecha'].max(), freq='D')

    def get_color(percentage):
        if percentage == 0:
            return 'rgba(255, 0, 0, 0.2)'  # Red
        elif 0 < percentage < 25:
            return 'rgba(255, 165, 0, 0.2)'  # Orange
        elif 25 <= percentage < 75:
            return 'rgba(255, 255, 0, 0.2)'  # Yellow
        else:
            return 'rgba(0, 255, 0, 0.2)'  # Green

    for row, (data, labors, title_icon) in enumerate([(maize_data, [l.replace('-maíz', '') for l in maize_labors], '🌽'), 
                                                      (beans_data, [l.replace('-frijol', '') for l in beans_labors], '🫘')], start=1):
        data_grouped = data.groupby(['Fecha', 'Labor'])['Informante'].apply(list).reset_index()
        data_grouped['Informantes'] = data_grouped['Informante'].apply(lambda x: ', '.join(x))
        data_grouped['Num_Informantes'] = data_grouped['Informante'].apply(len)

        if not data_grouped.empty:
            max_informantes = max(data_grouped['Num_Informantes'])
            marker_size = data_grouped['Num_Informantes'] * 5 if max_informantes > 0 else 10
        else:
            max_informantes = 0
            marker_size = 10

        fig.add_trace(go.Scatter(
            x=data_grouped['Fecha'],
            y=data_grouped['Labor'],
            mode='markers',
            marker=dict(
                size=marker_size,
                sizemode='area',
                sizeref=2. * max(data_grouped['Num_Informantes']) / (20. ** 2) if max_informantes > 0 else 1,
                sizemin=4
            ),
            name=f'Labores {"Maíz" if row == 1 else "Frijol"}',
            hovertemplate=
            '<b>Fecha</b>: %{x}<br>' +
            '<b>Labor</b>: %{y}<br>' +
            '<b>Informantes</b>: %{text}',
            text=data_grouped['Informantes']
        ), row=row, col=1)

        fig.update_yaxes(
            title=dict(text=title_icon, font=dict(size=50), standoff=0),
            title_standoff=20,
            categoryorder='array',
            categoryarray=labors,
            row=row, col=1
        )

        # Apply color coding
        for date in date_range:
            if date in data_grouped['Fecha'].values:
                percentage = data_grouped.loc[data_grouped['Fecha'] == date, 'Num_Informantes'].sum() / total_informants * 100
            else:
                percentage = 0

            color = get_color(percentage)

            fig.add_shape(
                type='rect',
                x0=date - pd.Timedelta(hours=12),
                y0=-0.5,
                x1=date + pd.Timedelta(hours=12),
                y1=len(labors) - 0.5,
                fillcolor=color,
                layer='below',
                line_width=0,
                row=row, col=1
            )

    fig.update_layout(
        height=600,  # Make the labor graphs smaller, matching the height of the climate ones
        title=dict(text=f'Actividades Agrícolas para: {selected_month}/{selected_year}', x=0.5),
        showlegend=True,
        margin=dict(l=100, r=50, t=90, b=90)
    )

    fig.update_xaxes(
        tickmode='auto',
        nticks=10,
        tickangle=0,
    )

    return fig

@app.callback(
    Output('condition-days-table', 'children'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_condition_days(selected_comunidad, selected_month, selected_year, _, selected_informant):
    if not selected_comunidad or not selected_month or not selected_year or not selected_informant:
        return html.Div("Seleccione una comunidad, un mes y un año.")

    with engine.connect() as conn:
        if selected_informant == 'Todos':
            query = f"""
            SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Granizada", "Helada"
            FROM table_clima27
            WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
            """
        else:
            query = f"""
            SELECT "Fecha", "Soleado", "Lluvioso", "Nublado", "Granizada", "Helada"
            FROM table_clima27
            WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Informante" = '{selected_informant}'
            """
        df = pd.read_sql(query, conn)

    df['Fecha'] = pd.to_datetime(df['Fecha'])

    # Map the string responses to numeric values, including NaN as 'Nada' = 0
    response_mapping = {'Nada': 0, 'Poco': 1, 'Normal': 2, 'Mucho': 3, None: 0}
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Granizada', 'Helada']:
        df[condition] = df[condition].map(response_mapping).fillna(0)  # Treat NaN as 'Nada'

    # Prepare display format for each condition
    data = []
    for condition in ['Soleado', 'Lluvioso', 'Nublado', 'Granizada', 'Helada']:
        condition_df = df.groupby('Fecha')[condition].mean().reset_index()
        condition_df['Día'] = condition_df['Fecha'].dt.strftime('%d')
        condition_df['Intensidad'] = condition_df[condition].round(1)
        
        if condition in ['Granizada', 'Helada']:
            condition_df = condition_df[condition_df['Intensidad'] > 0]
        else:
            condition_df = condition_df[condition_df['Intensidad'] > 2.5]
        
        if not condition_df.empty:
            data.append({"Riesgo": condition, "Días": condition_df.iloc[0]['Día'], "Intensidad": condition_df.iloc[0]['Intensidad']})
            for index, row in condition_df.iloc[1:].iterrows():
                data.append({"Riesgo": "", "Días": row['Día'], "Intensidad": row['Intensidad']})
        else:
            data.append({"Riesgo": condition, "Días": "No hay días que superen el umbral.", "Intensidad": ""})

    table = dash_table.DataTable(
        data=data,
        columns=[
            {"name": "Riesgo", "id": "Riesgo"},
            {"name": "Fecha", "id": "Días"},
            {"name": "Intensidad", "id": "Intensidad"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'color': 'white',
            'fontSize': '16px',
            'fontFamily': 'Arial'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(100, 150, 250)'
            },
            {
                'if': {'row_index': 'even'},
                'backgroundColor': 'rgb(80, 130, 220)'
            }
        ],
        style_header={
            'backgroundColor': 'rgb(50, 90, 180)',
            'fontWeight': 'bold',
            'color': 'white'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Fecha'},
                'textAlign': 'center',
                'whiteSpace': 'normal',
                'height': 'auto',
                'lineHeight': '1.2'
            },
            {
                'if': {'column_id': 'Intensidad'},
                'textAlign': 'center',
                'whiteSpace': 'normal',
                'height': 'auto',
                'lineHeight': '1.2'
                
            }
        ],
        style_table={
            'maxWidth': '800px',
            'margin': '0 auto',
            'marginTop': '20px'
        }
    )

    return html.Div([
        html.H4(f"Fechas e intensidades para {selected_month} en {selected_comunidad}", style={'textAlign': 'center', 'color': 'rgb(50, 90, 180)'}),
        table
    ], style={'margin-bottom': '50px'})

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


from collections import Counter

@app.callback(
    Output('climate-discrepancies-table', 'children'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children'),
     Input('labors-toggle', 'value')]
)
def update_climate_discrepancies_table(selected_comunidad, selected_month, selected_year, _, show_labors):
    if not selected_comunidad or not selected_month or not selected_year:
        return None

    with engine.connect() as conn:
        query = f"""
        SELECT "Fecha", "Informante", "Soleado", "Lluvioso", "Nublado", "Granizada", "Helada"
        FROM table_clima28
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
        ORDER BY "Fecha" ASC;
        """
        df = pd.read_sql(query, conn)

    if df.empty:
        return None

    df['Fecha'] = pd.to_datetime(df['Fecha'])

    # Filter out rows where all five climate responses are NaN or empty
    df = df.dropna(subset=['Soleado', 'Lluvioso', 'Nublado', 'Granizada', 'Helada'], how='all')

    discrepancy_data = []
    prev_condition = None

    condition_colors = {
        'Soleado': 'rgb(200, 220, 255)',
        'Lluvioso': 'rgb(200, 220, 255)',
        'Nublado': 'rgb(200, 220, 255)'
    }

    for condition in ['Soleado', 'Lluvioso', 'Nublado']:
        condition_df = df.groupby('Fecha')[['Informante', condition]].apply(lambda x: x.values.tolist()).reset_index()
        condition_df['Multiple_Responses'] = condition_df[0].apply(lambda x: len(set(response for _, response in x)) > 1)
        discrepancy_days = condition_df[condition_df['Multiple_Responses']]['Fecha'].tolist()

        for day in discrepancy_days:
            day_df = df[(df['Fecha'] == day) & (df[condition].notna())]
            informants_info = '\n'.join([f"• {informant} (Respuesta: {response if pd.notna(response) else 'Nada'})" for informant, response in day_df[['Informante', condition]].values])

            if condition != prev_condition:
                discrepancy_data.append({
                    'Categoría': condition,
                    'Fecha': day.strftime('%d'),
                    'Informantes': informants_info.replace('nan', 'Nada'),  # Replace 'nan' with 'Nada'
                    'Color': condition_colors[condition]
                })
                prev_condition = condition
            else:
                discrepancy_data.append({
                    'Categoría': '',
                    'Fecha': day.strftime('%d'),
                    'Informantes': informants_info.replace('nan', 'Nada'),  # Replace 'nan' with 'Nada'
                    'Color': condition_colors[condition]
                })

    if len(discrepancy_data) == 0:
        return html.Div('No se encontraron días con respuestas diferentes para este mes.')

    columns = [
        {'name': 'Categoría', 'id': 'Categoría'},
        {'name': 'Fecha', 'id': 'Fecha'},
        {'name': 'Informantes', 'id': 'Informantes'}
    ]

    style_data_conditional = []

    for condition, color in condition_colors.items():
        style_data_conditional.append({
            'if': {
                'filter_query': '{Categoría} = ' + condition
            },
            'backgroundColor': color
        })

    table = dash_table.DataTable(
        data=discrepancy_data,
        columns=columns,
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'whiteSpace': 'normal',
            'height': 'auto',
            'color': 'black'  # Black text color for readability
        },
        style_data_conditional=style_data_conditional,
        style_header={
            'backgroundColor': 'rgb(100, 150, 250)',  # Darker blue header
            'fontWeight': 'bold',
            'color': 'white'  # White header text
        },
        style_as_list_view=True,
        style_table={
            'width': '100%',
            'borderRadius': '10px',
            'overflow': 'hidden'
        },
        style_data={
            'whiteSpace': 'pre-wrap',
            'height': 'auto',
            'lineHeight': '1.2'
        }
    )

    return html.Div([
        html.H4(f"Días con Discrepancias Climáticas en {selected_comunidad} - {selected_month}/{selected_year}", style={'margin-bottom': '60px'}),
        table
    ], style={'margin-top': '20px', 'margin-bottom': '60px'})
    
@app.callback(
    Output('maiz-risks-table', 'children'),
    [Input('comunidad-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('labors-toggle', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_maiz_risks_table(selected_comunidad, selected_year, selected_month, show_labors, _, selected_informant):
    if 'show' in show_labors and selected_comunidad and selected_year and selected_month and selected_informant:
        with engine.connect() as conn:
            if selected_informant == 'Todos':
                query = f"""
                SELECT "Fecha", "Informante", "Riesgo helada-maíz", "Riesgo sequía-maíz", "Riesgo golpe de calor-maíz", "Riesgo inundación-maíz", "Riesgo plagas y enfermedades-maíz", "Riesgo granizada-maíz"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Año" = '{selected_year}' AND "Mes" = '{selected_month}'
                """
            else:
                query = f"""
                SELECT "Fecha", "Informante", "Riesgo helada-maíz", "Riesgo sequía-maíz", "Riesgo golpe de calor-maíz", "Riesgo inundación-maíz", "Riesgo plagas y enfermedades-maíz", "Riesgo granizada-maíz"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Año" = '{selected_year}' AND "Mes" = '{selected_month}' AND "Informante" = '{selected_informant}'
                """
            df = pd.read_sql(query, conn)


        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Día'] = df['Fecha'].dt.strftime('%d')

        risks = ['Helada', 'Sequía', 'Golpe de calor', 'Inundación', 'Plagas y enfermedades', 'Granizada']
        risk_columns = ['Riesgo helada-maíz', 'Riesgo sequía-maíz', 'Riesgo golpe de calor-maíz', 'Riesgo inundación-maíz', 'Riesgo plagas y enfermedades-maíz', 'Riesgo granizada-maíz']

        informants = df['Informante'].unique()

        table_data = []
        for risk, column in zip(risks, risk_columns):
            risk_data = {'Riesgo': risk}
            for informant in informants:
                risk_data[informant] = ', '.join(df[(df[column] == '1.0') & (df['Informante'] == informant)]['Día'].tolist())
            table_data.append(risk_data)

        columns = [{'name': 'Riesgo', 'id': 'Riesgo'}] + [{'name': informant, 'id': informant} for informant in informants]

        table = dash_table.DataTable(
            data=table_data,
            columns=columns,
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'whiteSpace': 'normal',
                'height': 'auto',
                'backgroundColor': 'rgb(230, 240, 250)',  # Light blue cell background
                'color': 'black'  # Black text color for readability
            },
            style_header={
                'backgroundColor': 'rgb(100, 150, 250)',  # Darker blue header
                'fontWeight': 'bold',
                'color': 'white'  # White header text
            },
            style_as_list_view=True,
            style_table={
                'width': '100%',
                'borderRadius': '10px',
                'overflow': 'hidden'
            },
            style_data={
                'whiteSpace': 'normal',
                'height': 'auto',
                'lineHeight': '15px'
            }
        )

        return html.Div([
            html.H4(f"Fechas del mes con problemas para el cultivo de Maíz en {selected_comunidad} - {selected_month}/{selected_year}", style={'margin-bottom': '60px'}),
            table
        ], style={'margin-top': '20px', 'margin-bottom': '60px'})
    else:
        return ""

@app.callback(
    Output('frijol-risks-table', 'children'),
    [Input('comunidad-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('labors-toggle', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_frijol_risks_table(selected_comunidad, selected_year, selected_month, show_labors, _, selected_informant):
    if 'show' in show_labors and selected_comunidad and selected_year and selected_month and selected_informant:
        with engine.connect() as conn:
            if selected_informant == 'Todos':
                query = f"""
                SELECT "Fecha", "Informante", "Riesgo helada-frijol", "Riesgo sequía-frijol", "Riesgo golpe de calor-frijol", "Riesgo inundación-frijol", "Riesgo plagas y enfermedades-frijol", "Riesgo granizada-frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Año" = '{selected_year}' AND "Mes" = '{selected_month}'
                """
            else:
                query = f"""
                SELECT "Fecha", "Informante", "Riesgo helada-frijol", "Riesgo sequía-frijol", "Riesgo golpe de calor-frijol", "Riesgo inundación-frijol", "Riesgo plagas y enfermedades-frijol", "Riesgo granizada-frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Año" = '{selected_year}' AND "Mes" = '{selected_month}' AND "Informante" = '{selected_informant}'
                """
            df = pd.read_sql(query, conn)

        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Día'] = df['Fecha'].dt.strftime('%d')

        risks = ['Helada', 'Sequía', 'Golpe de calor', 'Inundación', 'Plagas y enfermedades', 'Granizada']
        risk_columns = ['Riesgo helada-frijol', 'Riesgo sequía-frijol', 'Riesgo golpe de calor-frijol', 'Riesgo inundación-frijol', 'Riesgo plagas y enfermedades-frijol', 'Riesgo granizada-frijol']

        informants = df['Informante'].unique()

        table_data = []
        for risk, column in zip(risks, risk_columns):
            risk_data = {'Riesgo': risk}
            for informant in informants:
                risk_data[informant] = ', '.join(df[(df[column] == '1') & (df['Informante'] == informant)]['Día'].tolist())
            table_data.append(risk_data)

        columns = [{'name': 'Riesgo', 'id': 'Riesgo'}] + [{'name': informant, 'id': informant} for informant in informants]

        table = dash_table.DataTable(
            data=table_data,
            columns=columns,
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'whiteSpace': 'normal',
                'height': 'auto',
                'backgroundColor': 'rgb(230, 240, 250)',  # Light blue cell background
                'color': 'black'  # Black text color for readability
            },
            style_header={
                'backgroundColor': 'rgb(100, 150, 250)',  # Darker blue header
                'fontWeight': 'bold',
                'color': 'white'  # White header text
            },
            style_as_list_view=True,
            style_table={
                'width': '100%',
                'borderRadius': '10px',
                'overflow': 'hidden'
            },
            style_data={
                'whiteSpace': 'normal',
                'height': 'auto',
                'lineHeight': '15px'
            }
        )

        return html.Div([
            html.H4(f"Fechas del mes con problemas para el cultivo de Frijol en {selected_comunidad} - {selected_month}/{selected_year}", style={'margin-bottom': '60px'}),
            table
        ], style={'margin-top': '20px', 'margin-bottom': '60px'})
    else:
        return ""

@app.callback(
    Output('graphs-container', 'style'),
    [Input('labors-toggle', 'value')]
)
def toggle_visibility(show_labors):
    if 'show' in show_labors:
        return {'display': 'none'}
    else:
        return {'display': 'block'}


@app.callback(
    Output('maiz-status-graph', 'figure'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('labors-toggle', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_maiz_status_graph(selected_comunidad, selected_month, selected_year, show_labors, _, selected_informant):
    if 'show' in show_labors and selected_comunidad and selected_month and selected_year and selected_informant:
        with engine.connect() as conn:
            if selected_informant == 'Todos':
                query = f"""
                SELECT "Fecha", "Estado del maíz"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
                ORDER BY "Fecha" ASC;
                """
            else:
                query = f"""
                SELECT "Fecha", "Estado del maíz"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Informante" = '{selected_informant}'
                ORDER BY "Fecha" ASC;
                """
            df = pd.read_sql(query, conn)

        df['Fecha'] = pd.to_datetime(df['Fecha'])
        response_mapping = {'Mal': 1, 'Regular': 2, 'Bien': 3}
        df['Estado del maíz'] = df['Estado del maíz'].map(response_mapping)

        temp_df = df.groupby('Fecha')['Estado del maíz'].agg(['mean', 'count']).reset_index()
        temp_df.rename(columns={'mean': 'Response', 'count': 'Count'}, inplace=True)

        informants_df = df.groupby('Fecha').size().reset_index(name='Informants')
        temp_df = pd.merge(temp_df, informants_df, on='Fecha', how='left')

        fig = go.Figure(data=go.Scatter(
            x=temp_df['Fecha'],
            y=temp_df['Response'],
            mode='lines+markers',
            line=dict(width=6, color='#2ca02c'),  # Increase line width and set color
            marker=dict(size=16, color='#2ca02c'),  # Increase marker size and set color
            name='Estado del maíz',
            hovertemplate=
            '<b>Fecha</b>: %{x}<br>' +
            '<b>Índice</b>: %{y}<br>' +
            '<b>Número de Informantes</b>: %{text}',
            text=temp_df['Informants']
        ))

        fig.update_layout(
            title=f'Estado del Maíz para {selected_comunidad} - {selected_month}/{selected_year}',
            xaxis_title='Fecha',
            yaxis_title='Índice de Estado',
            yaxis=dict(
                tickvals=[1, 2, 3],
                ticktext=['Mal', 'Regular', 'Bien'],
                range=[0.5, 3.5]  # Set the range to always include all options
            ),
            margin=dict(l=60, r=20, t=80, b=40),  # Adjust margins for a tighter plot
            height=300  # Set a fixed height for the plot
        )

        return fig
    else:
        return go.Figure()  # Return an empty figure if conditions are not met

@app.callback(
    Output('frijol-status-graph', 'figure'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('labors-toggle', 'value'),
     Input('upload-timestamp', 'children'),
     Input('informant-dropdown', 'value')]
)
def update_frijol_status_graph(selected_comunidad, selected_month, selected_year, show_labors, _, selected_informant):
    if 'show' in show_labors and selected_comunidad and selected_month and selected_year and selected_informant:
        with engine.connect() as conn:
            if selected_informant == 'Todos':
                query = f"""
                SELECT "Fecha", "Estado del frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
                ORDER BY "Fecha" ASC;
                """
            else:
                query = f"""
                SELECT "Fecha", "Estado del frijol"
                FROM table_clima28
                WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}' AND "Informante" = '{selected_informant}'
                ORDER BY "Fecha" ASC;
                """
            df = pd.read_sql(query, conn)

        df['Fecha'] = pd.to_datetime(df['Fecha'])
        response_mapping = {'Mal': 1, 'Regular': 2, 'Bien': 3}
        df['Estado del frijol'] = df['Estado del frijol'].map(response_mapping)

        temp_df = df.groupby('Fecha')['Estado del frijol'].agg(['mean', 'count']).reset_index()
        temp_df.rename(columns={'mean': 'Response', 'count': 'Count'}, inplace=True)

        informants_df = df.groupby('Fecha').size().reset_index(name='Informants')
        temp_df = pd.merge(temp_df, informants_df, on='Fecha', how='left')

        fig = go.Figure(data=go.Scatter(
            x=temp_df['Fecha'],
            y=temp_df['Response'],
            mode='lines+markers',
            line=dict(width=6, color='#ff7f0e'),  # Increase line width and set color
            marker=dict(size=16, color='#ff7f0e'),  # Increase marker size and set color
            name='Estado del frijol',
            hovertemplate=
            '<b>Fecha</b>: %{x}<br>' +
            '<b>Índice</b>: %{y}<br>' +
            '<b>Número de Informantes</b>: %{text}',
            text=temp_df['Informants']
        ))

        fig.update_layout(
            title=f'Estado del Frijol para {selected_comunidad} - {selected_month}/{selected_year}',
            xaxis_title='Fecha',
            yaxis_title='Índice de Estado',
            yaxis=dict(
                tickvals=[1, 2, 3],
                ticktext=['Mal', 'Regular', 'Bien'],
                range=[0.5, 3.5]  # Set the range to always include all options
            ),
            margin=dict(l=60, r=20, t=80, b=40),  # Adjust margins for a tighter plot
            height=300  # Set a fixed height for the plot
        )

        return fig
    else:
        return go.Figure()  # Return an empty figure if conditions are not met

@app.callback(
    Output('informant-ranking', 'children'),
    [Input('comunidad-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('upload-timestamp', 'children')]
)
def update_informant_ranking(selected_comunidad, selected_month, selected_year, _):
    if not selected_comunidad or not selected_month or not selected_year:
        return ""

    with engine.connect() as conn:
        query = f"""
        SELECT "Informante", COUNT(DISTINCT "Fecha") AS "Días Respondidos"
        FROM table_clima28
        WHERE "Comunidad" = '{selected_comunidad}' AND "Mes" = '{selected_month}' AND "Año" = '{selected_year}'
        GROUP BY "Informante"
        ORDER BY "Días Respondidos" DESC
        """
        df = pd.read_sql(query, conn)

    if df.empty:
        return html.Div("No hay datos disponibles para el mes y año seleccionados.")

    # Create a styled table with a smaller, blue theme
    table = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{'name': col, 'id': col} for col in df.columns],
        style_header={
            'backgroundColor': 'rgb(100, 150, 250)',  # Blue header
            'fontWeight': 'bold',
            'color': 'white'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '6px',
            'color': 'black',
            'fontSize': '14px'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(230, 240, 250)'  # Lighter blue for odd rows
            }
        ]
    )

    return html.Div([
        html.H4(f"Ranking de Informantes para {selected_comunidad} - {selected_month}/{selected_year}", style={'margin-bottom': '20px'}),
        table,
        html.Br()  # Add a line break after the table
    ])

@app.callback(
    [Output('maiz-status-graph', 'style'),
     Output('frijol-status-graph', 'style')],
    [Input('labors-toggle', 'value')]
)
def toggle_graph_visibility(show_labors):
    if 'show' in show_labors:
        return {'display': 'block'}, {'display': 'block'}  # Make graphs visible
    else:
        return {'display': 'none'}, {'display': 'none'}  # Hide graphs



if __name__ == '__main__':
    app.run_server(debug=True)




