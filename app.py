import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavLink("Home", href="/"),
        dbc.NavLink("Standings", href="/standings"),
        dbc.NavLink("Teams", href="/team"),
        dbc.NavLink("Games", href="/game"),
        dbc.NavLink("Players", href="/player"),
    ],
    brand="NHL Dashboard",
    brand_href="/",
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
    app.run(debug=True)