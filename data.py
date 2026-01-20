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



# Create a connection pool
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=db_config["host"],
    port=db_config["port"],
    user=db_config["user"],
    password=db_config["password"],
    database=db_config["database"]
)

# local connection
# connection_pool = mysql.connector.connect(
#     pool_name="mypool",
#     pool_size=5,
#     host=db_config_local["host"],
#     port=db_config_local["port"],
#     user=db_config_local["user"],
#     password=db_config_local["password"],
#     database=db_config_local["database"]
# )

#cursor = connection.cursor()

seasons = pd.DataFrame()
teams = pd.DataFrame()

connection = connection_pool.get_connection()
try:
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM seasons
    """)
    seasons = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])

    available_seasons = sorted(seasons['season_id'].unique())#was start_year so that it looks nice but season_id works for the current functionality

    cursor.execute("""
        SELECT * FROM teams
    """)
    teams = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
finally:
    cursor.close()
    connection.close()


def slug_to_name_and_id_and_abv(slug):
    team_name = slug.replace('-', ' ').lower()
    team = teams[teams['team_name'].str.lower() == team_name]
    if not team.empty:
        return team['team_name'].values[0], int(team['team_id'].values[0]), team['team_abbreviation'].values[0]
    return None, None, None

def get_team_abv(team):
    # If team is an int, treat as team_id
    result = None

    if isinstance(team, (int, np.integer)):
        result = teams[teams['team_id'] == team]
    # If team is a string, treat as team_name
    elif isinstance(team, str):
        result = teams[teams['team_name'] == team]

    if result is not None and not result.empty:
        return str(result['team_abbreviation'].values[0])

    return None

def get_team_id(team):
    # Try name first, then abbreviation
    result = teams[teams['team_name'] == team]
    if result.empty and 'team_abbreviation' in teams.columns:
        result = teams[teams['team_abbreviation'] == team]

    if not result.empty:
        return int(result['team_id'].values[0])
    return None

def get_team_name(team_id = None, team_abv = None):
    # Accepts team_id (int) or team_abbreviation (str)
    if team_id is not None:
        return teams[teams['team_id'] == team_id]['team_name'].values[0]
    
    if team_abv is not None:
        return teams[teams['team_abbreviation'] == team_abv]['team_name'].values[0]
    
    return None

def get_logo(team_slug = None, team_id = None):
    if team_slug is not None:
        team_id = slug_to_name_and_id_and_abv(team_slug)[1]

    if team_id is not None:
        team = teams[teams['team_id'] == team_id]
    else:
        return None

    if not team.empty and 'team_abbreviation' in team.columns:
        abv = team['team_abbreviation'].values[0]
        return f"/NHLDashboard/assets/logos/{abv}_logo.svg"
    return None

def get_season_end_standings_df(season):
    seasons_end_standings_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT *
            FROM seasons_end_standings
            WHERE season_id = %s
            AND games_played > 0
        """, (int(season),))

        seasons_end_standings_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

        # Data cleaning and merging
    column_mapping = {
        'team_name': 'Team',
        'games_played': 'GP',
        'wins': 'W',
        'losses': 'L',
        'ot_losses': 'OTL',
        'points': 'PTS',
        'conference_name': 'Conference',
        'division_name': 'Division',
        'season_id': 'Season'
    }
    seasons_end_standings_df = seasons_end_standings_df.merge(
        teams[['team_id', 'team_name']],
        left_on='team_id',
        right_on='team_id',
        how='left'
    )
    seasons_end_standings_df.rename(columns=column_mapping, inplace=True)
    seasons_end_standings_df = seasons_end_standings_df.sort_values(by='PTS', ascending=False)
    seasons_end_standings_df['slug'] = seasons_end_standings_df['Team'].str.replace(' ', '-').str.lower()
    teams['slug'] = teams['team_name'].str.replace(' ', '-').str.lower()

    return seasons_end_standings_df[seasons_end_standings_df['Season'] == season]

def get_roster_players_df(season, team_slug):
    roster_players = pd.DataFrame()

    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
        SELECT * FROM roster_players
                       WHERE season_id = %s
                       AND team_id = %s
        """, (season_id, team_id))
        roster_players = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    return roster_players[(roster_players['season_id'] == season_id) & (roster_players['team_id'] == team_id)]

def get_team_schedule_df(season, team_slug):
    schedule_df = pd.DataFrame()

    team_id = slug_to_name_and_id_and_abv(team_slug)[1]
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s AND (home_team_id = %s OR away_team_id = %s)
        """, (season_id, team_id, team_id))
        schedule_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    return schedule_df

def get_game_df(game_id):
    game_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE game_id = %s
        """, (game_id,))
        game_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return game_df

def get_game_events_df(game_id):
    events_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE game_id = %s
        """, (game_id,))
        events_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return events_df

def get_games_of_season(season = None):
    if season is None:
        season = get_current_season()

    games_df = pd.DataFrame()
    season_id = int(season)

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s
            ORDER BY date
        """, (season_id,))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df

def get_games_around_date(season=None, days_before=10, days_after=10):
    games_df = pd.DataFrame()

    if season is None:
        season = get_current_season()

    season_id = int(season)
    current_date = date.today()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE season_id = %s
            AND date BETWEEN DATE_SUB(%s, INTERVAL %s DAY) 
                        AND DATE_ADD(%s, INTERVAL %s DAY)
            ORDER BY date
        """, (season_id, current_date, days_before, current_date, days_after))
        games_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return games_df

def get_current_season():
    result = None

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT DISTINCT season_id FROM games
            ORDER BY season_id DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if result:
        return result[0]
    return None

def get_most_recent_game():
    game_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE game_outcome != ''
            ORDER BY date DESC
            LIMIT 1
        """)
        game_df = pd.DataFrame([cursor.fetchone()], columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return game_df

def get_player(player_id):
    player_df = pd.DataFrame()

    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM players
            WHERE player_id = %s
        """, (player_id,))
        player_df = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()
    return player_df

def get_player_name(player_id, default="Unknown"):
    try:
        if player_id is None:
            return default
        df = get_player(player_id)
        if df.empty:
            return default
        if 'skaterFullName' in df.columns and not pd.isnull(df['skaterFullName'].values[0]):
            return str(df['skaterFullName'].values[0])
        return default
    except Exception:
        return default
    
def get_teams_ordered():
    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT s.team_id, MAX(s.season_id) AS last_season, t.team_name
            FROM seasons_end_standings s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.games_played > 0
            GROUP BY s.team_id, t.team_name
        """)
        teams_last_season = pd.DataFrame(cursor.fetchall(), columns=[i[0] for i in cursor.description])
    finally:
        cursor.close()
        connection.close()

    teams_last_season = teams_last_season.sort_values(by=['last_season', 'team_name'], ascending=[False, True])
    return teams_last_season

        






















def make_standings_table(df):
    #if season_id is before 19831984 remove OTL column
    if 'Season' in df.columns and not df.empty and df['Season'].iloc[0] < 19831984:
        display_columns = ['Team', 'GP', 'W', 'L', 'PTS']
    else:
        display_columns = ['Team', 'GP', 'W', 'L', 'OTL', 'PTS']
    rows = []
    for _, row in df.iterrows():
        team_logo = html.Img(
            src=get_logo(team_slug=row['slug']),
            alt=f"{row['Team']} logo",
            style={"height": "20px", "marginRight": "8px", "verticalAlign": "middle"}
        )
        team_link = dcc.Link([team_logo, row['Team']], href=f"/NHLDashboard/team/{row['slug']}")
        cells = [html.Td(team_link, className="team-link-standings")] + [html.Td(row[col]) for col in display_columns if col != 'Team']
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col, className="team-link-standings" if col == "Team" else "") for col in display_columns]))] +
        [html.Tbody(rows)],
        striped=True, bordered=True, hover=True, responsive=True
    )

def make_team_table(df):
    display_columns = ['firstName','lastName', 'sweaterNumber', 'positionCode', 'heightInCentimeters', 'weightInKilograms', 'birthDate', 'birthCountry']
    rows = []
    for _, row in df.iterrows():
        cells = [html.Td(row[col]) for col in display_columns]
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
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
        home_abv = get_team_abv(row['home_team_id'])
        away_abv = get_team_abv(row['away_team_id'])
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

        logo_home = get_logo(team_id=row['home_team_id'])
        logo_away = get_logo(team_id=row['away_team_id'])
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
    for _, row in df.iterrows():
        home_abv = get_team_abv(row['home_team_id'])
        away_abv = get_team_abv(row['away_team_id'])
        game_id = row['game_id']  # Assuming you have a game_id column
        game_date = row['date'].strftime("%b %d")

        score_section = None
        if pd.notnull(row['away_score']) and pd.notnull(row['home_score']):
            score_section = html.P(f"Score: {int(row['away_score'])} - {int(row['home_score'])}", className="score")


        games.append(
            dcc.Link(
                html.Div([
                    html.H3(f"{away_abv} @ {home_abv}"),
                    html.P(f"Date: {game_date}"),
                    score_section
                ], className="big-game-card"),
                href=f"/NHLDashboard/game/{game_id}"
            )
        )
    return html.Div(games, className="schedule-grid-container")


def make_game_card(df):
    if df.empty:
        return html.Div("Game not found.")#, className="game-card")

    row = df.iloc[0]
    home_abv = get_team_abv(row['home_team_id'])
    away_abv = get_team_abv(row['away_team_id'])

    home_score = row['home_score'] if pd.notnull(row['home_score']) else "N/A"
    away_score = row['away_score'] if pd.notnull(row['away_score']) else "N/A"
    
    return html.Div([
        html.H3(f"{away_abv} @ {home_abv}"),
        html.P(f"Date: {row['date']}"),
        html.P(f"Score: {away_score} - {home_score}"),
    ], className="big-game-card")#

def make_game_page(game_id):
    df_game = get_game_df(game_id)
    df_events = get_game_events_df(game_id)

    if df_game.empty:
        return html.Div("Game not found.")

    row = df_game.iloc[0]
    home_abv = get_team_abv(row['home_team_id'])
    away_abv = get_team_abv(row['away_team_id'])

    home_score = row['home_score'] if pd.notnull(row['home_score']) else "N/A"
    away_score = row['away_score'] if pd.notnull(row['away_score']) else "N/A"

    if pd.notnull(row['home_score']) and pd.notnull(row['away_score']):
        score_or_time = f"{away_score} - {home_score}"
    else:
        eastern = pytz.timezone('US/Eastern')  # Define the EST timezone
        if pd.notnull(row['start_time_UTC']):
            game_datetime_UTC = row['start_time_UTC']
            game_datetime_UTC = game_datetime_UTC.replace(tzinfo=pytz.UTC)  # Declare it as UTC

            # Convert to EST
            game_datetime_EST = game_datetime_UTC.astimezone(eastern)

            # Format the time as "10:00 PM EST"
            formatted_time_EST = game_datetime_EST.strftime('%I:%M %p')
            score_or_time = f"{formatted_time_EST} EST"
        else:
            score_or_time = "Start time TBA"

    top_section = html.Div([
        # Row: logos and matchup
        html.Div([
            html.Img(src=get_logo(team_id=row['away_team_id']), alt=f"{away_abv} logo", style={"height": "60px", "marginRight": "1em"}),
            html.H2(f"{away_abv} @ {home_abv}", style={"margin": "0 1em", "textAlign": "center"}),
            html.Img(src=get_logo(team_id=row['home_team_id']), alt=f"{home_abv} logo", style={"height": "60px", "marginLeft": "1em"}),
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

    home_name = get_team_name(team_id = home_id)
    away_name = get_team_name(team_id = away_id)

    home_logo = get_logo(team_id=home_id)
    away_logo = get_logo(team_id=away_id)


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
                    (f"Assist 1: {get_player_name(row['assist1_player'], default='N/A')}" if pd.notnull(row['assist1_player']) and row['assist1_player'] != '' else '')
                    +
                    (f", Assist 2: {get_player_name(row['assist2_player'], default='N/A')}" if pd.notnull(row['assist2_player']) and row['assist2_player'] != '' else '')
                ) if row['type_desc_key'] == 'Goal' else ''
            ),
            axis=1
        )

        home_display['Details'] = home_side.apply(
            lambda row: (
                (
                    (f"Assist 1: {get_player_name(row['assist1_player'], default='N/A')}" if pd.notnull(row['assist1_player']) and row['assist1_player'] != '' else '')
                    +
                    (f", Assist 2: {get_player_name(row['assist2_player'], default='N/A')}" if pd.notnull(row['assist2_player']) and row['assist2_player'] != '' else '')
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
    team_df['type_desc_key'] = team_df['type_desc_key'].str.capitalize()

    team_df = team_df[team_df['type_desc_key'].isin(['Goal', 'Penalty', 'Shot' ])]
    #event_id, period_number, period_type, time_in_period, time_remaining, situation_code, type_code, type_desc_key, sort_order, x_coord, y_coord, zone_code, shot_type, blocking_Player_id, shooting_player_id, goalie_in_net_id, player_id, event_owner_team_id, away_sog, home_sog, hitting_player_id, hittee_player_id, reason, secondary_reason, losing_player_id, winning_player_id, scoring_player_id, assist1_player_id, assist2_player_id, highlight_clip_sharing_url, duration, served_by_player_id, drawn_by_player_id, committed_by_player_id

    team_sc_df = pd.DataFrame()
    #for each row if it is a goal get the scoring_player_id, assist1_player_id, assist2_player_id
    for _, event in team_df.iterrows():
        if event['type_desc_key'] == 'Goal':
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
                'event_player_owner_name': get_player_name(scoring_player_id)
            }

        elif event['type_desc_key'] == 'Penalty':
            committed_by_player_id = event['committed_by_player_id']
            new_row = {
                'type_desc_key': 'Penalty',
                'period_number': event['period_number'],
                'time_in_period': event['time_in_period'],
                'event_player_owner_id': committed_by_player_id,
                'event_player_owner_name': get_player_name(committed_by_player_id)
            }

        elif event['type_desc_key'] == 'Shot':
            shooting_player_id = event['shooting_player_id']
            new_row = {
                'type_desc_key': 'Shot',
                'period_number': event['period_number'],
                'time_in_period': event['time_in_period'],
                'event_player_owner_id': shooting_player_id,
                'event_player_owner_name': get_player_name(shooting_player_id)
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


    home_team_name = get_team_name(team_id=home_team_id)
    away_team_name = get_team_name(team_id=away_team_id)



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