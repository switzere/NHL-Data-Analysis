import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    requests_pathname_prefix="/NHLDashboard/",
    routes_pathname_prefix="/NHLDashboard/"
)

print(dash.page_registry)


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

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    navbar,
    dash.page_container
])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=False)
