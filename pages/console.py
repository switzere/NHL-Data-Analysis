import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import mysql.connector
from config import db_config
import pandas as pd

# Register the page
import dash

dash.register_page(__name__, path="/console", name="SQL Console")

def layout(**kwargs):
    # Fetch table/column info for display
    import mysql.connector
    from config import db_config

    table_info = []
    try:
        connection = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"]
        )
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            columns = [col[0] for col in cursor.fetchall()]
            # Get one example row
            example_values = []
            try:
                cursor.execute(f"SELECT * FROM `{table}` LIMIT 1;")
                row = cursor.fetchone()
                if row:
                    example_values = [str(val) if val is not None else "NULL" for val in row]
                else:
                    example_values = ["(no data)"] * len(columns)
            except Exception:
                example_values = ["(error)"] * len(columns)
            table_info.append((table, list(zip(columns, example_values))))
        cursor.close()
        connection.close()
    except Exception as e:
        table_info = [("Error fetching table info", [(str(e),"")])]

    # Render table info as HTML (column name + example value)
    table_list = [
        html.Details([
            html.Summary(table),
            html.Table([
                html.Thead(html.Tr([html.Th("Column"), html.Th("Example Value")])) ,
                html.Tbody([
                    html.Tr([html.Td(col), html.Td(val)]) for col, val in columns_and_vals
                ])
            ], style={"marginBottom": "1em"})
        ]) for table, columns_and_vals in table_info
    ]

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("SQL Console", className="text-center my-4"),
                html.H5("Available Tables and Columns:"),
                html.Div(table_list, style={"marginBottom": "2em", "maxHeight": "300px", "overflowY": "auto", "border": "1px solid #ccc", "padding": "1em", "background": "#f9f9f9"}),
                dcc.Textarea(
                    id="sql-query-input",
                    placeholder="Enter your SELECT SQL query here...",
                    style={"width": "100%", "height": 100},
                ),
                html.Br(),
                dbc.Button("Run Query", id="run-query-btn", color="primary", className="mt-2"),
                html.Div(id="sql-query-error", style={"color": "red", "marginTop": "1em"}),
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div(id="sql-query-results", className="table-responsive", style={"marginTop": "2em"})
            ], width=12)
        ])
    ], fluid=True)

@dash.callback(
    Output("sql-query-results", "children"),
    Output("sql-query-error", "children"),
    Input("run-query-btn", "n_clicks"),
    State("sql-query-input", "value"),
    prevent_initial_call=True
)
def run_sql_query(n_clicks, query):
    import re, time, logging
    MAX_ROWS = 200
    TIMEOUT_SECONDS = 5
    LOG_FILE = "sql_console_queries.log"

    # Log the query
    try:
        with open(LOG_FILE, "a") as logf:
            logf.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {query}\n")
    except Exception:
        pass  # Don't block on logging errors

    # Only allow SELECT statements (no semicolons, no comments, no dangerous keywords)
    if not query or not query.strip().lower().startswith("select"):
        return None, "Only SELECT statements are allowed."
    if ";" in query or re.search(r"(--|/\*|drop|delete|update|insert|alter|create|replace|truncate|grant|revoke|exec|call|set|use)\b", query, re.IGNORECASE):
        return None, "Query contains forbidden keywords or characters."

    # Limit result size by enforcing LIMIT if not present
    if not re.search(r"limit\s+\d+", query, re.IGNORECASE):
        query = query.rstrip(";") + f" LIMIT {MAX_ROWS}"

    # Use a dedicated, non-pooled connection for the console
    try:
        connection = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"]
        )
        # Set session to read-only if supported
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION TRANSACTION READ ONLY;")
        except Exception:
            pass  # Not all DBs support this
        # Enforce timeout (MySQL: max_execution_time in ms)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SET SESSION max_execution_time={TIMEOUT_SECONDS * 1000};")
        except Exception:
            pass
        # Run the query
        try:
            df = pd.read_sql(query, connection)
        finally:
            connection.close()
        if df.empty:
            return html.P("No results found."), None
        return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True), None
    except Exception as e:
        return None, f"Error: {str(e)}"
    