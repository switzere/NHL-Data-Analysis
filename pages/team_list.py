import dash
from dash import html
import dash_bootstrap_components as dbc
from data import get_teams_ordered, slug_to_name_and_id_and_abv, get_logo

dash.register_page(__name__, path="/team", name="Teams")

def layout(**kwargs):
    teams_df = get_teams_ordered()
    team_links = []
    for _, team in teams_df.iterrows():
        team_name = team['team_name']
        team_id = team['team_id']
        slug = team_name.replace(' ', '-').lower()
        logo_src = get_logo(team_id=team_id)
        team_links.append(
            dbc.Row([
                dbc.Col(html.Img(src=logo_src, style={"height": "40px", "marginRight": "1em"}), width="auto"),
                dbc.Col(html.A(team_name, href=f"/NHLDashboard/team/{slug}", className="h4"), width="auto")
            ], align="center", className="mb-2")
        )
    return dbc.Container([
        dbc.Row(dbc.Col(html.H1("Select a Team", className="text-center my-4"), width=12)),
        dbc.Row(dbc.Col(html.Div(team_links), width=12))
    ], fluid=True)