import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from data import get_games_around_date, make_schedule_row, get_current_season, available_seasons, get_games_of_season

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder="assets",
    requests_pathname_prefix="/NHLDashboard/",
    routes_pathname_prefix="/NHLDashboard/"
)


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavLink("Home", href="/NHLDashboard"),
        dbc.NavLink("Standings", href="/NHLDashboard/standings"),
        dbc.NavLink("Teams", href="/NHLDashboard/team"),
        dbc.NavLink("Games", href="/NHLDashboard/game"),
        dbc.NavLink("Players", href="/NHLDashboard/player"),
    ],
    brand="NHL Dashboard",
    brand_href="/NHLDashboard",
    color="primary",
    dark=True,
    sticky="top",
)

year_dropdown = dcc.Dropdown(
    id='season-dropdown',
    options=[{'label': s, 'value': s} for s in available_seasons],
    value=available_seasons[-1],
    clearable=False,
    className="floating-dropdown"  # Add the floating-dropdown class directly
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
        year_dropdown,
        schedule_row         
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
    #print(f"Current pathname: {pathname}")  # Debugging
    if pathname.endswith('/'):
        pathname = pathname[:-1]

    # dropdown_pages = ["/NHLDashboard/standings", "/NHLDashboard/team/<team_slug>"]

    # if pathname in dropdown_pages:
    #     return {'display': 'block'}
    if pathname == "/NHLDashboard/standings" or pathname.startswith("/NHLDashboard/team/"):
        return {'display': 'block'}
    return {'display': 'none'}

@app.callback(
    Output('schedule-row-container', 'children'),
    Input('daily-refresh', 'n_intervals')
)
def render_schedule_row(_):
    df_schedule = get_games_around_date()
    #df_schedule = get_games_of_season()
    return make_schedule_row(df_schedule)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=False)
