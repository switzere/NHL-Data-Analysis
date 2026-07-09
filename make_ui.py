import mysql.connector
from mysql.connector import pooling
import pandas as pd
from config import db_config, db_config_local, db_config_local_socket
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date, datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pytz

import data

def make_standings_table(df):
    #if season_id is before 19831984 remove OTL column
    if 'Season' in df.columns and not df.empty and df['Season'].iloc[0] < 19831984:
        display_columns = ['Team', 'GP', 'W', 'L', 'PTS']
    else:
        display_columns = ['Team', 'GP', 'W', 'L', 'OTL', 'PTS', 'WC']

    df = df.sort_values(by='PTS', ascending=False).reset_index(drop=True)
    
    rows = []
    for index, row in df.iterrows():
        team_logo = html.Img(
            src=data.get_logo(team_slug=row['slug']),
            alt=f"{row['Team']} logo",
            style={"height": "20px", "marginRight": "8px", "verticalAlign": "middle"}
        )
        team_link = dcc.Link([team_logo, row['Team']], href=f"/NHLDashboard/team/{row['slug']}")
        row_style = {"borderBottom": "2px solid black"} if index == 2 else {}
        highlight_wc = row.get('WC') in (7, 8)

        cell_style = {**row_style, "backgroundColor": "#dbe9ff"} if highlight_wc else {}

        cells = [html.Td(team_link, className="team-link-standings", style=cell_style)] + [html.Td(row[col], style=cell_style) for col in display_columns if col != 'Team']
        rows.append(html.Tr(cells, style=row_style))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col, className="team-link-standings" if col == "Team" else "") for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )

def make_team_table(df):
    display_columns = ['firstName','lastName', 'sweaterNumber', 'positionCode', 'games_played', 'goals', 'assists', 'points', 'penalty_minutes', 'plus_minus']
    rows = []
    for _, row in df.iterrows():
        player_id = row.get('player_id')[0]
        # Make the first and last name a clickable link to the player page
        name_link = (
            dcc.Link(
                f"{row['firstName']} {row['lastName']}",
                href=f"/NHLDashboard/player/{player_id}",
                className="player-link"
            )
            if player_id is not None else f"{row['firstName']} {row['lastName']}"
        )
        cells = [html.Td(name_link)] + [html.Td(row[col]) for col in display_columns[2:]]
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Player")] + [html.Th(col) for col in display_columns[2:]]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )

def make_schedule_row(df):
    current_date = date.today()
 
    games = []
    dates = []

    is_id_set = False
    last_game_date = None

    # constants must match your CSS (.game-card min-width and gap)
    CARD_WIDTH = 120  # px, matches .game-card min-width
    GAP = 0          # px, matches .dates-row/.games-row gap

    # precompute number of games per date
    date_counts = df.groupby('date').size().to_dict()


    for _, row in df.iterrows():
        home_abv = data.get_team_abv(row['home_team_id'])
        away_abv = data.get_team_abv(row['away_team_id'])
        game_id = row['game_id']  # Assuming you have a game_id column
        # make readable date Dec 10 example
        game_date = row['date']#.strftime("%b %d")

        if last_game_date != game_date:
            count = date_counts.get(game_date, 1)
            total_width = count * CARD_WIDTH + max(0, count - 1) * GAP
            label = game_date.strftime("%b %d") if count == 1 else game_date.strftime("%B %d, %Y")

            dates.append(
                html.Div(
                    label,
                    className="schedule-date",
                    style={
                        "minWidth": f"{total_width}px",
                        "width": f"{total_width}px",
                        "textAlign": "center",
                        "flex": "0 0 auto"
                    },
                    **{"data-date": game_date.isoformat()}
                )
            )
            last_game_date = game_date

        logo_home = data.get_logo(team_id=row['home_team_id'])
        logo_away = data.get_logo(team_id=row['away_team_id'])
        logos_section = html.Div([
            html.Img(src=logo_away, alt=f"{away_abv} logo", style={"height": "30px", "marginRight": "1em"}),
            html.Img(src=logo_home, alt=f"{home_abv} logo", style={"height": "30px"})
        ], className="logos")

        teams_section = html.P(f"{away_abv} @ {home_abv}", className="teams")


        #use game_outcome to see if game has been played

        eastern = pytz.timezone('US/Eastern')  # Define the EST timezone
        score_section = None
        time_section = None
        if pd.notnull(row['start_time_UTC']) and pd.isnull(row['game_outcome']):
            game_datetime_UTC = row['start_time_UTC']
            game_datetime_UTC = game_datetime_UTC.replace(tzinfo=pytz.UTC)  # Declare it as UTC

            # Convert to EST
            game_datetime_EST = game_datetime_UTC.astimezone(eastern)

            # Format the time as "10:00 PM EST"
            formatted_time_EST = game_datetime_EST.strftime('%I:%M %p')
            time_section = html.P(f"{formatted_time_EST} EST", className="time")

        elif pd.notnull(row['away_score']) and pd.notnull(row['home_score']):
            OTSO = ' OT' if row['game_outcome'] == 'OT' else (' SO' if row['game_outcome'] == 'SO' else '')
            score_section = html.P(f"{int(row['away_score'])} - {int(row['home_score'])} Final{OTSO}", className="score")



        games.append(
            dcc.Link(
                html.Div([
                    # html.P(f"{game_date}", className="date"),
                    # html.P(f"{away_abv} @ {home_abv}", className="teams"),
                    logos_section,
                    teams_section,
                    score_section,
                    time_section
                ], className=f"game-card {game_date}"
                #,                    **({"id": game_id_attr} if game_id_attr else {})
                ),
                href=f"/NHLDashboard/game/{game_id}"
            )
        )

    schedule_row = html.Div(
        html.Div(
            [
                html.Div(dates, className="dates-row"),
                html.Div(games, className="games-row"),
            ],
            className="horizontal-scroll__inner"
        ),
        className="horizontal-scroll__wrapper schedule-container",
        id="schedule-scroll-wrapper",
        **{"data-today": current_date.isoformat()}   
    )

    return schedule_row


def make_schedule_grid(df):
    games = []
    standings = data.get_season_end_standings_df(data.get_current_season())
    last_10 = data.get_most_recent_games(num=10)

    
    for _, row in df.iterrows():
        home_abv = data.get_team_abv(row['home_team_id'])
        away_abv = data.get_team_abv(row['away_team_id'])
        game_id = row['game_id']  # Assuming you have a game_id column
        game_start_etc = data.UTC_to_EST(row['start_time_UTC'])
        game_date = row['date'].strftime("%b %d")

        home_logo = data.get_logo(team_id=row['home_team_id'])
        away_logo = data.get_logo(team_id=row['away_team_id'])

        interest_icons_home = make_interest_icons(row['home_team_id'], standings, last_10)
        interest_icons_away = make_interest_icons(row['away_team_id'], standings, last_10)

        score_section = None
        if pd.notnull(row['away_score']) and pd.notnull(row['home_score']):
            score_section = html.P(f"Score: {int(row['away_score'])} - {int(row['home_score'])}", className="score")

        games.append(
            dcc.Link(
                html.Div([
                    html.Section([
                        html.H3(f"{away_abv} @ {home_abv}"),
                        html.P(f"{game_id:08d}")  # Format game_id as an 8-digit number
                    ], className="ticket-sub"),
                    html.Section([
                        html.Div([
                            html.Img(src=away_logo, alt=f"{away_abv} logo"),
                            html.Img(src=home_logo, alt=f"{home_abv} logo")
                        ], className="logos"),
                        html.P(f"{game_date} - {game_start_etc.strftime('%I:%M %p')} EST", className="game-time"),
                        html.Div([
                            interest_icons_away
                        ], className="interest-icons-away"),
                        html.Div([
                            interest_icons_home
                        ], className="interest-icons-home")
                    ], className="ticket-main")
                ], className="ticket"),
                href=f"/NHLDashboard/game/{game_id}"
            )
        )

    return html.Div(games, className="schedule-grid-container")


def make_game_card(df):
    if df.empty:
        return html.Div("Game not found.")#, className="game-card")

    row = df.iloc[0]
    home_abv = data.get_team_abv(row['home_team_id'])
    away_abv = data.get_team_abv(row['away_team_id'])

    home_score = row['home_score'] if pd.notnull(row['home_score']) else "N/A"
    away_score = row['away_score'] if pd.notnull(row['away_score']) else "N/A"
    
    return html.Div([
        html.H3(f"{away_abv} @ {home_abv}"),
        html.P(f"Date: {row['date']}"),
        html.P(f"Score: {away_score} - {home_score}"),
    ], className="big-game-card")#

def make_game_page(game_id):
    df_game = data.get_game_df(game_id)
    df_events = data.get_game_events_df(game_id)

    if df_game.empty:
        return html.Div("Game not found.")

    row = df_game.iloc[0]
    home_abv = data.get_team_abv(row['home_team_id'])
    away_abv = data.get_team_abv(row['away_team_id'])

    home_score = row['home_score'] if pd.notnull(row['home_score']) else "N/A"
    away_score = row['away_score'] if pd.notnull(row['away_score']) else "N/A"

    if pd.notnull(row['home_score']) and pd.notnull(row['away_score']):
        score_or_time = f"{away_score} - {home_score}"
    else:
        if pd.notnull(row['start_time_UTC']):

            # Convert to EST
            game_datetime_EST = data.UTC_to_EST(row['start_time_UTC'])

            # Format the time as "10:00 PM EST"
            formatted_time_EST = game_datetime_EST.strftime('%I:%M %p')
            score_or_time = f"{formatted_time_EST} EST"
        else:
            score_or_time = "Start time TBA"

    top_section = html.Div([
        # Row: logos and matchup
        html.Div([
            html.Img(src=data.get_logo(team_id=row['away_team_id']), alt=f"{away_abv} logo", style={"height": "60px", "marginRight": "1em"}),
            html.H2(f"{away_abv} @ {home_abv}", style={"margin": "0 1em", "textAlign": "center"}),
            html.Img(src=data.get_logo(team_id=row['home_team_id']), alt=f"{home_abv} logo", style={"height": "60px", "marginLeft": "1em"}),
        ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
        # Row: score and date, centered below
        html.Div([
            html.H2(f"{score_or_time}", className="text-center mb-4"),
            html.H2(f"{row['date']}", className="text-center mb-4")
        ], style={"textAlign": "center", "width": "100%"})
    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "justifyContent": "center"})

    scoresheet = html.Div()
    if not df_events.empty:
        scoresheet = make_scoresheet(df_game, df_events)

    events_graphic = html.Div()
    if not df_events.empty:
        events_graphic = make_events_graphic(df_events, home_team_id=row['home_team_id'], away_team_id=row['away_team_id'])


    return html.Div([
        top_section,
        scoresheet,
        events_graphic
    ], className="")#

def make_scoresheet(df_game, df_events):
    if df_game.empty:
        return html.Div("No game data available for this game.")
    
    row = df_game.iloc[0]

    home_id = row['home_team_id']
    away_id = row['away_team_id']

    home_name = data.get_team_name(team_id = home_id)
    away_name = data.get_team_name(team_id = away_id)

    home_logo = data.get_logo(team_id=home_id)
    away_logo = data.get_logo(team_id=away_id)


    if df_game['game_outcome'].isnull().values[0]:
        charts = html.Div("Game has not been played yet.")
    else:
        away_side = make_scoresheet_team_side(df_events, away_id)
        home_side = make_scoresheet_team_side(df_events, home_id)

        away_display = away_side[['type_desc_key', 'period_number', 'time_in_period', 'event_player_owner_name']].rename(
            columns={
                "type_desc_key": "Event",
                "event_player_owner_name": "Player",
                "period_number": "Period",
                "time_in_period": "Time"
            }
        )
        home_display = home_side[['type_desc_key', 'period_number', 'time_in_period', 'event_player_owner_name']].rename(
            columns={
                "type_desc_key": "Event",
                "event_player_owner_name": "Player",
                "period_number": "Period",
                "time_in_period": "Time"
            }
        )

        #make details column for assists in both displays
        away_display['Details'] = away_side.apply(
            lambda row: (
                (
                    (f"Assist 1: {data.get_player_name(row['assist1_player'], default='N/A')}" if pd.notnull(row['assist1_player']) and row['assist1_player'] != '' else '')
                    +
                    (f", Assist 2: {data.get_player_name(row['assist2_player'], default='N/A')}" if pd.notnull(row['assist2_player']) and row['assist2_player'] != '' else '')
                ) if row['type_desc_key'] == 'Goal' else ''
            ),
            axis=1
        )

        home_display['Details'] = home_side.apply(
            lambda row: (
                (
                    (f"Assist 1: {data.get_player_name(row['assist1_player'], default='N/A')}" if pd.notnull(row['assist1_player']) and row['assist1_player'] != '' else '')
                    +
                    (f", Assist 2: {data.get_player_name(row['assist2_player'], default='N/A')}" if pd.notnull(row['assist2_player']) and row['assist2_player'] != '' else '')
                ) if row['type_desc_key'] == 'Goal' else ''
            ),
            axis=1
        )


        charts = dbc.Row([
            dbc.Col(dbc.Table.from_dataframe(
                away_display,
                striped=True, bordered=True, hover=True, responsive=True
            ), width=6),
            dbc.Col(dbc.Table.from_dataframe(
                home_display,
                striped=True, bordered=True, hover=True, responsive=True
            ), width=6)
        ])


    sc = html.Div([
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.Img(src=away_logo, alt=f"{away_name} logo", style={"height": "30px", "marginRight": "10px"}),
                    html.H4(f"{away_name}", className="text-center", style={"display": "inline-block", "verticalAlign": "middle"})
                ], className="text-center"),
                width=6
            ),
            dbc.Col(
                html.Div([
                    html.Img(src=home_logo, alt=f"{home_name} logo", style={"height": "30px", "marginRight": "10px"}),
                    html.H4(f"{home_name}", className="text-center", style={"display": "inline-block", "verticalAlign": "middle"})
                ], className="text-center"),
                width=6
            )
        ]),
        charts
    ], className="scoresheet-card")


    return html.Div([
        sc
    ], className="scoresheet")


def make_scoresheet_team_side(df_events, team_id):
    #get goals, assists, penalties, shots from events table for players on the away team from df
    team_df = df_events[df_events['event_owner_team_id'] == team_id]
    #team_df['type_desc_key'] = team_df['type_desc_key'].str.capitalize()

    team_df = team_df[team_df['type_desc_key'].isin(['goal', 'penalty', 'shot' ])]
    #event_id, period_number, period_type, time_in_period, time_remaining, situation_code, type_code, type_desc_key, sort_order, x_coord, y_coord, zone_code, shot_type, blocking_Player_id, shooting_player_id, goalie_in_net_id, player_id, event_owner_team_id, away_sog, home_sog, hitting_player_id, hittee_player_id, reason, secondary_reason, losing_player_id, winning_player_id, scoring_player_id, assist1_player_id, assist2_player_id, highlight_clip_sharing_url, duration, served_by_player_id, drawn_by_player_id, committed_by_player_id

    team_sc_df = pd.DataFrame()
    #for each row if it is a goal get the scoring_player_id, assist1_player_id, assist2_player_id
    for _, event in team_df.iterrows():
        if event['type_desc_key'] == 'goal':
            scoring_player_id = event['scoring_player_id']
            assist1_player_id = event['assist1_player_id']
            assist2_player_id = event['assist2_player_id']

            new_row = {
                'type_desc_key': 'Goal',
                'period_number': event['period_number'],
                'time_in_period': event['time_in_period'],
                'event_player_owner_id': scoring_player_id,
                'assist1_player': assist1_player_id,
                'assist2_player': assist2_player_id,
                'event_player_owner_name': data.get_player_name(scoring_player_id)
            }

        elif event['type_desc_key'] == 'penalty':
            committed_by_player_id = event.get('committed_by_player_id') if pd.notnull(event.get('committed_by_player_id')) else event.get('served_by_player_id')
            new_row = {
                'type_desc_key': 'Penalty',
                'period_number': event['period_number'],
                'time_in_period': event['time_in_period'],
                'event_player_owner_id': committed_by_player_id,
                'event_player_owner_name': data.get_player_name(committed_by_player_id)
            }

        elif event['type_desc_key'] == 'shot':
            shooting_player_id = event['shooting_player_id']
            new_row = {
                'type_desc_key': 'Shot',
                'period_number': event['period_number'],
                'time_in_period': event['time_in_period'],
                'event_player_owner_id': shooting_player_id,
                'event_player_owner_name': data.get_player_name(shooting_player_id)
            }

        team_sc_df = pd.concat([team_sc_df, pd.DataFrame([new_row])], ignore_index=True)

    #order team_sc_df by period_number(1,2,3) and time_in_period(00:00 to 20:00)
    team_sc_df['period_number'] = team_sc_df['period_number'].astype(int)
    team_sc_df['timedelta'] = team_sc_df['time_in_period'].apply(lambda x: f"00:{x}" if pd.notnull(x) and ':' in str(x) and len(str(x).split(':')) == 2 else x)
    team_sc_df['timedelta'] = pd.to_timedelta(team_sc_df['timedelta'])
    team_sc_df = team_sc_df.sort_values(by=['period_number', 'timedelta'], ascending=[True, True])

    return team_sc_df



# game_id int PK 
# season_id int 
# game_type int 
# date date 
# home_team_id int 
# away_team_id int 
# home_score int 
# away_score int 
# game_outcome varchar(255) 
# winning_goalie_id int 
# winning_goal_scorer_id int 
# series_status_round int

def make_events_graphic(df, home_team_id, away_team_id):
    if df.empty:
        return html.Div("No events found for this game.")


    home_team_name = data.get_team_name(team_id=home_team_id)
    away_team_name = data.get_team_name(team_id=away_team_id)



    # Map team IDs to names for legend clarity
    team_id_to_name = {
        home_team_id: f"{home_team_name}",
        away_team_id: f"{away_team_name}"
    }
    df['team_label'] = df['event_owner_team_id'].map(team_id_to_name)

    #remove delayed-penalty events
    df = df[df['type_desc_key'] != 'delayed-penalty']

    # Add hover_text column if missing
    if 'hover_text' not in df.columns:
        df = df.copy()
        df['hover_text'] = (
            "Type: " + df['type_desc_key'].astype(str) +
            "<br>Period: " + df['period_number'].astype(str) +
            "<br>Time: " + df['time_in_period'].astype(str) +
            "<br>Team: " + df['team_label'].astype(str)
        )

    fig = go.Figure()

    team_colors = {f"{home_team_name}": "orange", f"{away_team_name}": "purple"}

    for team_label in team_colors:
        for event_type in df['type_desc_key'].unique():
            team_events = df[(df['team_label'] == team_label) & (df['type_desc_key'] == event_type)]
            if not team_events.empty:
                symbol = "x" if event_type == "goal" else "circle"
                size = 12 if event_type == "goal" else 8
                opacity = 1 if event_type == "goal" else 0.9
                is_visible = True if event_type in ["goal", "shot-on-goal"] else "legendonly"

                fig.add_trace(go.Scatter(
                    x=team_events['x_coord'],
                    y=team_events['y_coord'],
                    legendgroup=team_label,
                    legendgrouptitle_text=team_label if event_type == "goal" else None,  # Only set once per group
                    name=event_type.capitalize(),
                    mode="markers",
                    marker=dict(color=team_colors[team_label], symbol=symbol, size=size, opacity=opacity),
                    hovertext=team_events['hover_text'] if 'hover_text' in team_events else None,
                    hoverinfo="text",
                    visible=is_visible
                ))

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        images=[
            dict(
                source="/NHLDashboard/assets/rink-template-2.png",
                xref="x",
                yref="y",
                x=-100,
                y=42,
                sizex=200,
                sizey=-84,
                sizing="stretch",
                layer="below",
                opacity=0.8
            )
        ],
        # width=1250,
        # height=600,
        xaxis=dict(range=[-100, 100]),
        yaxis=dict(range=[-42, 42]),
        title='Event Locations',
        legend=dict(groupclick="toggleitem", itemdoubleclick="toggleothers")
    )

    return html.Div(
        dcc.Graph(
            figure=fig,
            style={
                "width": "80%",
                "aspectRatio": "2.1", #really 2.35 but this looks more natural
                "height": "auto",
                "minHeight": "300px"
            }
        ),
        style={
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
            "width": "100%"
        }
    )

def make_team_cusp_figure(team_id, season_id=20252026):
    # You must pass a valid DB cursor from your app context

    games = data.get_teams_games_season(team_id=team_id, season_id=season_id)

    team_name = data.get_team_name(team_id=team_id)

    games = games.sort_values(by='date')
    games['points'] = 0
    for game_index in games.index:
        row = games.loc[game_index]
        if (row['home_team_id'] == team_id) and (row['home_score'] > row['away_score']):
            games.at[game_index, 'points'] = 2
        elif (row['away_team_id'] == team_id) and (row['away_score'] > row['home_score']):
            games.at[game_index, 'points'] = 2
        elif (row['game_outcome'] in ['OT', 'SO']):
            games.at[game_index, 'points'] = 1
    games['cumulative_points'] = games['points'].cumsum()

    x = np.arange(len(games) + 1)
    y = np.insert(games['cumulative_points'].values, 0, 0)

    xC = np.arange(0, 82 + 1)
    cusp_line = 1.13 * xC

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='lines+markers', name=team_name, line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=xC, y=cusp_line, mode='lines', name='Cusp Line (slope=1.13)', line=dict(color='red', dash='dash')
    ))
    fig.update_layout(
        title=f'{team_name} Cumulative Points in {season_id} Season',
        xaxis_title='Games Played',
        yaxis_title='Cumulative Points',
        xaxis=dict(range=[0, 82], tickmode='linear', dtick=10),
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=40, r=40, t=60, b=40),
        template='plotly_white'
    )
    return dcc.Graph(
        figure=fig,
        style={
            "width": "100%",
            "maxWidth": "1800px",
            "margin": "0 auto",
            "height": "800px"
        }
    )

def make_interest_icons(team_id, standings, last_10_all):
    # Placeholder icons, replace with actual icons as needed
    last_10 = last_10_all[(last_10_all['team_id'] == team_id)]
    #get the number of wins in the last 10 games
    wins = 0
    for _, row in last_10.iterrows():
        if row['team_score'] > row['opponent_score']:
            wins += 1

    #🏁🏆🧊

    streak = ""
    if wins >= 7:
        streak = "🔥"
    elif wins <= 3:
        streak = "🧊"

    race = ""
    points = standings[standings['team_id'] == team_id]['points'].values[0]
    division = standings[standings['team_id'] == team_id]['division_name'].values[0]
    conference = standings[standings['team_id'] == team_id]['conference_name'].values[0]

    top_division_points = standings[(standings['division_name'] == division)]['points'].max()
    top_division_games_remaining = 82 - standings[(standings['division_name'] == division) & (standings['wildcard_rank'] == 1)]['games_played'].values[0]

    wildcard_points = standings[(standings['conference_name'] == conference) & (standings['wildcard_rank'] == 8)]['points'].values[0]


    if (points > wildcard_points - (top_division_games_remaining/2) and points < wildcard_points + (top_division_games_remaining/2)) and (top_division_games_remaining < 20):
        race = "🏁"
    elif (points > top_division_points - (top_division_games_remaining/2)) and (top_division_games_remaining < 40):
        race = "🏆"


    

    return html.Div([
        html.Span(streak, className='interest-icon') if streak else [],
        html.Span(race, className='interest-icon') if race else []
    ])

def make_player_table(player_id):
    df = data.get_player_seasons(player_id)
    if df.empty:
        return html.Div("Player not found.")

    #display_columns = ['player_id','skaterFullName', 'total_goals', 'total_assists', 'total_points', 'total_penalty_minutes', 'total_games_played', 'total_plus_minus', 'birth_date', 'birth_country']
    display_columns = ['goals', 'assists', 'points', 'penalty_minutes', 'games_played', 'season_id', 'team_abbreviations', 'time_on_ice_per_game']
    rows = []
    for _, r in df.iterrows():
        cells = [html.Td(r[col]) for col in display_columns]
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )