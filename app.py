import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_games_around_date, available_seasons
from make_ui import make_schedule_row

app = dash.Dash(
    __name__,
    title="NHL Data Dashboard",
    update_title=None,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder="assets",
    requests_pathname_prefix="/NHLDashboard/",
    routes_pathname_prefix="/NHLDashboard/"
)

app._favicon = ("7s_64.png")

year_dropdown = dcc.Dropdown(
    id='season-dropdown',
    options=[{'label': s, 'value': s} for s in available_seasons],
    value=available_seasons[-1],
    clearable=False
)

navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        
        dbc.Collapse(
            dbc.Nav(
                [
                    dbc.NavLink("Home", href="/NHLDashboard"),
                    dbc.NavLink("Standings", href="/NHLDashboard/standings"),
                    dbc.NavLink("Teams", href="/NHLDashboard/team"),
                    dbc.NavLink("Players", href="/NHLDashboard/player"),
                ],
                navbar=True,
                className="nav-links"
            ),
            id="navbar-collapse",
            navbar=True,
        ),
       year_dropdown
    ], className="navbar-custom"),
    className="navbar-top",
    #sticky="top",
    
)

# Schedule Row
schedule_row = dbc.Row(dbc.Col(html.Div(id="schedule-row-container"), width=12))


# App Layout
app.layout = html.Div([
    dcc.Store(id='selected-season', data=available_seasons[-1]),
    dcc.Interval(id='daily-refresh', interval=24*60*60*1000, n_intervals=0),  # refresh every 24 hours
    #dcc.Interval(id='daily-refresh', interval=10*60*1000, n_intervals=0),  # 10 minutes * 60 seconds * 1000 ms
    dcc.Location(id='url', refresh=False),
    navbar,
    html.Div([
        schedule_row,
    ], className="dropdown-and-schedule-container-wrapper"),  # Ensure the dropdown is positioned relative to this container
    dash.page_container
])

@app.callback(
    Output('selected-season', 'data'),
    Input('season-dropdown', 'value')
)
def update_selected_season(selected_season):
    return selected_season

@app.callback(
    Output('season-dropdown', 'style'),
    Input('url', 'pathname')
)
def toggle_dropdown_visibility(pathname):
    pathname = (pathname or "").rstrip("/")
    if pathname in ("/NHLDashboard/standings",) or pathname.startswith("/NHLDashboard/team/"):
        return {"display": "block"}
    return {"display": "none"}

    # dropdown_pages = ["/NHLDashboard/standings", "/NHLDashboard/team/<team_slug>"]

    # if pathname in dropdown_pages:
    #     return {'display': 'block'}
    # if pathname == "/NHLDashboard/standings" or pathname.startswith("/NHLDashboard/team/"):
    #     return {'display': 'block'}
    # return {'display': 'none'}

@app.callback(
    Output('schedule-row-container', 'children'),
    Input('daily-refresh', 'n_intervals')
)
def render_schedule_row(_):
    df_schedule = get_games_around_date()
    #df_schedule = get_games_of_season()
    return make_schedule_row(df_schedule)

@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [dash.dependencies.State("navbar-collapse", "is_open")]
)
def toggle_navbar(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=False)
