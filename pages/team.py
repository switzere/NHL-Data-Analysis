import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from data import get_roster_players_df, make_team_table, get_team_schedule_df, make_schedule_row, get_logo, slug_to_name_and_id_and_abv, get_teams_ordered

dash.register_page(__name__, path_template="/team/<team_slug>", name="Team Page")  

def layout(team_slug=None, **kwargs):
    return dbc.Container([
        dbc.Row(
            dbc.Col(html.Div(id="team-content"), width=12)
        )
    ], fluid=True)

@dash.callback(
    Output("team-content", "children"),
    Input("selected-season", "data"),
    State("url", "pathname")
)

def update_team_page(selected_season, pathname):
    team_slug = pathname.split("/")[-1]  # Extract the last part of the URL
    if not team_slug:
        return html.P("No team selected.")

        # team_list = get_teams_ordered()
        # team_links = [html.Li(html.A(slug_to_name_and_id_and_abv(team['team_slug'])[0], href=f"/team/{team['team_slug']}")) for _, team in team_list.iterrows()]
        # return dbc.Container([
        #     dbc.Row(
        #         dbc.Col(html.H1("Select a Team", className="text-center my-4"), width=12)
        #     ),
        #     dbc.Row(
        #         dbc.Col(html.Ul(team_links), width=12)
        #     )
        # ], fluid=True)
        
    
    team_name = slug_to_name_and_id_and_abv(team_slug)[0]

    df_roster = get_roster_players_df(selected_season, team_slug)
    df_schedule = get_team_schedule_df(selected_season, team_slug)

    img_src = get_logo(team_slug=team_slug)


    return dbc.Container([
        dbc.Row(
            dbc.Col([
                html.H1([
                    html.Img(src=img_src, alt=f"{team_slug} logo", style={"height": "60px", "marginRight": "1em", "verticalAlign": "middle"}),
                    f"{team_name} ({selected_season})"
                ], className="text-center my-4"),
            ], width=12)
        ),
        dbc.Row(
            dbc.Col([html.H2(f"Schedule"), make_schedule_row(df_schedule)], width=12)
            ),
        dbc.Row([
            dbc.Col([html.H2("Roster", className="text-center"), make_team_table(df_roster)], width=12)
        ])
    ], fluid=True)