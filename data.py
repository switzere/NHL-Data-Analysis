import mysql.connector
from mysql.connector import pooling
import pandas as pd
from config import db_config, db_config_local, db_config_local_socket
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date, datetime
import plotly.express as px
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
    team = teams[teams['slug'] == slug]
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

def get_team_name(team):
    # Accepts team_id (int), team_name (str), or team_abbreviation (str)
    if isinstance(team, int):
        result = teams[teams['team_id'] == team]
    elif isinstance(team, str):
        # Try name first, then abbreviation
        result = teams[teams['team_name'] == team]
        if result.empty and 'team_abbreviation' in teams.columns:
            result = teams[teams['team_abbreviation'] == team]
    else:
        result = pd.DataFrame()
    if not result.empty:
        return result['team_name'].values[0]
    return None

def get_logo(team_slug):
    team = teams[teams['slug'] == team_slug]
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

def get_games_around_date(season, days_before=10, days_after=10):
    games_df = pd.DataFrame()

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










def make_standings_table(df):
    display_columns = ['Team', 'GP', 'W', 'L', 'OTL', 'PTS']
    rows = []
    for _, row in df.iterrows():
        team_link = dcc.Link(row['Team'], href=f"/NHLDashboard/team/{row['slug']}")
        cells = [html.Td(team_link)] + [html.Td(row[col]) for col in display_columns if col != 'Team']
        print(team_link)
        print(cells)
        rows.append(html.Tr(cells))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th(col) for col in display_columns]))] +
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
    is_id_set = False

    for _, row in df.iterrows():
        home_abv = get_team_abv(row['home_team_id'])
        away_abv = get_team_abv(row['away_team_id'])
        game_id = row['game_id']  # Assuming you have a game_id column
        # make readable date Dec 10 example
        game_date = row['date'].strftime("%b %d")
        game_timestamp_UTC = row['start_time_UTC']

        time_section = None
        if pd.notnull(row['start_time_UTC']):
            # Convert UTC timestamp to EST
            utc = pytz.utc
            eastern = pytz.timezone('US/Eastern')
            game_datetime_UTC = game_timestamp_UTC.tz_localize(utc)  # Localize as UTC
            game_datetime_EST = game_datetime_UTC.astimezone(eastern)  # Convert to EST

            # Format the time as "7:00 PM"
            formatted_time_EST = game_datetime_EST.strftime('%I:%M %p')
            time_section = html.P(f"Start Time (EST): {formatted_time_EST}", className="start-time")


        score_section = None
        if pd.notnull(row['away_score']) and pd.notnull(row['home_score']):
            score_section = html.P(f"Score: {int(row['away_score'])} - {int(row['home_score'])}", className="score")


        games.append(
            dcc.Link(
                html.Div([
                    html.P(f"{game_date}", className="date"),
                    html.P(f"{away_abv} @ {home_abv}", className="teams"),
                    score_section,
                    time_section
                ], className="game-card"
                #,                    **({"id": game_id_attr} if game_id_attr else {})
                ),
                href=f"/NHLDashboard/game/{game_id}"
            )
        )
    return html.Div(games, className="schedule-container")


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
                    html.H2(f"{away_abv} @ {home_abv}"),
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

def make_events_graphic(df):
    if df.empty:
        return html.Div("No events found for this game.")
    
    # Add hover_text column if missing
    if 'hover_text' not in df.columns:
        df = df.copy()
        df['hover_text'] = (
            "Type: " + df['type_desc_key'].astype(str) +
            "<br>Period: " + df['period_number'].astype(str) +
            "<br>Time: " + df['time_in_period'].astype(str)
        )

    fig = px.scatter(
        df,
        x='x_coord',
        y='y_coord',
        color='type_desc_key',
        hover_name='type_desc_key',  # Main hover label
        hover_data={'hover_text': True, 'x_coord': True, 'y_coord': True, 'type_desc_key': False},
        labels={'x_coord': 'X Coordinate', 'y_coord': 'Y Coordinate'},
        range_x=[-100, 100],   # Set x-axis range
        range_y=[42, -42],      # Set y-axis range and reverse
        title='Event Locations'
    )

    fig.update_layout(
        images=[
            dict(
                source="/NHLDashboard/assets/rink-template-2.png",
                xref="x",
                yref="y",
                x=-100,  # Align the left edge of the image with the left edge of the x-axis
                y=-42,    # Align the top edge of the image with the top of the y-axis
                sizex=200,  # Match the width of the x-axis range (-100 to 100)
                sizey=84,   # Match the height of the y-axis range (42 to -42)
                sizing="stretch",
                layer="below"
            )
        ],
        width=1250,
        height=600
    )

    
    return dcc.Graph(figure=fig)