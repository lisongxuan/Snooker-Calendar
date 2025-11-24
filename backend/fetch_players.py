import configparser
import sqlalchemy as sqla
import time
from snooker.api import SnookerOrgApi
from sqlalchemy.ext.declarative import declarative_base
from query_data import get_current_season
# Function to load configuration from config.txt
def load_config(filename='config.txt'):
    config = configparser.ConfigParser()
    config.read(filename)

    # Load database configuration
    db_config = {key: value for key, value in config['database'].items()}

    # Load API configuration
    api_config = {key: value for key, value in config['api'].items()}

    return db_config, api_config

# Load configurations
db_config, api_config = load_config()

# Create SQLAlchemy engine
engine = sqla.create_engine(f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}", pool_size=10, max_overflow=-1)
Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    id = sqla.Column(sqla.Integer, primary_key=True)
    type = sqla.Column(sqla.Integer)
    first_name = sqla.Column(sqla.String(255))
    middle_name = sqla.Column(sqla.String(255))
    last_name = sqla.Column(sqla.String(255))
    team_name = sqla.Column(sqla.String(255))
    team_number = sqla.Column(sqla.Integer)
    team_season = sqla.Column(sqla.Integer)
    short_name = sqla.Column(sqla.String(255))
    nationality = sqla.Column(sqla.String(255))
    sex = sqla.Column(sqla.String(10))
    bio_page = sqla.Column(sqla.Text)
    born = sqla.Column(sqla.String(50))
    twitter = sqla.Column(sqla.String(255))
    surname_first = sqla.Column(sqla.Boolean)
    license = sqla.Column(sqla.String(255))
    club = sqla.Column(sqla.String(255))
    url = sqla.Column(sqla.Text)
    photo = sqla.Column(sqla.Text)
    photo_source = sqla.Column(sqla.Text)
    first_season_as_pro = sqla.Column(sqla.Integer)
    last_season_as_pro = sqla.Column(sqla.Integer)
    info = sqla.Column(sqla.Text)
    num_ranking_titles = sqla.Column(sqla.Integer)
    num_maximums = sqla.Column(sqla.Integer)
    died = sqla.Column(sqla.String(50))

    def __init__(self, player_data):
        self.id = player_data.ID
        self.type = player_data.Type
        self.first_name = player_data.FirstName
        self.middle_name = player_data.MiddleName
        self.last_name = player_data.LastName
        self.team_name = player_data.TeamName
        self.team_number = player_data.TeamNumber
        self.team_season = player_data.TeamSeason
        self.short_name = player_data.ShortName
        self.nationality = player_data.Nationality
        self.sex = player_data.Sex
        self.bio_page = player_data.BioPage
        self.born = player_data.Born
        self.twitter = player_data.Twitter
        self.surname_first = player_data.SurnameFirst
        self.license = player_data.License
        self.club = player_data.Club
        self.url = player_data.URL
        self.photo = player_data.Photo
        self.photo_source = player_data.PhotoSource
        self.first_season_as_pro = player_data.FirstSeasonAsPro
        self.last_season_as_pro = player_data.LastSeasonAsPro
        self.info = player_data.Info
        self.num_ranking_titles = player_data.NumRankingTitles
        self.num_maximums = player_data.NumMaximums
        self.died = player_data.Died

class Ranking(Base):
    __tablename__ = 'rankings'
    position = sqla.Column(sqla.Integer, primary_key=True)
    player_id = sqla.Column(sqla.Integer)
    sum_value = sqla.Column(sqla.Float)

    def __init__(self, ranking_data):
        self.position = ranking_data.Position
        self.player_id = ranking_data.PlayerID
        self.sum_value = ranking_data.Sum

def init_db():
    Base.metadata.create_all(engine)

def fetch_single_player(player_id, client=None, session=None):
    """
    Fetch and store a single player's information.

    Args:
        player_id (int): The ID of the player to fetch
        client: Optional API client instance
        session: Optional database session instance

    Returns:
        bool: True if successful, False if failed
    """
    # Initialize client if not provided
    if client is None:
        client = SnookerOrgApi(headers={'X-Requested-By': api_config['x_requested_by']})

    # Initialize session if not provided
    if session is None:
        DBSession = sqla.orm.sessionmaker(bind=engine)
        session = DBSession()
        should_close_session = True
    else:
        should_close_session = False

    try:
        print(f"Fetching player {player_id}...")

        # Get player data
        player_data = client.player(player_id)

        # Create or update player in database
        player = Player(player_data)
        session.merge(player)  # merge will insert or update
        session.commit()

        print(f"Successfully stored/updated player {player_id}: {player_data.FirstName} {player_data.LastName}")
        return True

    except Exception as e:
        print(f"Error fetching/storing player {player_id}: {e}")
        session.rollback()
        return False

    finally:
        if should_close_session:
            session.close()

def fetch_and_store_players():
    # Initialize API client
    client = SnookerOrgApi(headers={'X-Requested-By': api_config['x_requested_by']})

    # Get rankings
    rankings = client.rankings(api_config['ranking_type'], get_current_season())
    print(f"Found {len(rankings)} rankings")

    # Create database session
    DBSession = sqla.orm.sessionmaker(bind=engine)
    session = DBSession()

    # Store rankings first
    print("Storing rankings...")
    for ranking in rankings:
        ranking_record = Ranking(ranking)
        session.merge(ranking_record)  # merge will insert or update
    session.commit()
    print("Rankings stored successfully")

    # Process each ranking
    for i, ranking in enumerate(rankings):
        player_id = ranking.PlayerID

        success = fetch_single_player(player_id, client=client, session=session)
        if not success:
            continue

        # Wait between requests (except for the last one)
        if i < len(rankings) - 1:
            wait_time = int(api_config['request_delay_seconds'])
            print(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)

    session.close()
    print("Finished fetching all players")

if __name__ == '__main__':
    init_db()

    # You can now call fetch_single_player individually:
    fetch_single_player(376)  # Fetch player with ID 5

    # Or fetch all players from rankings:
    #fetch_and_store_players()