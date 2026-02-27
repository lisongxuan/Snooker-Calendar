import configparser
import sqlalchemy as sqla
import time
from snooker.api import SnookerOrgApi
from query_data import get_current_season
from sqlalchemy.ext.declarative import declarative_base

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

class Event(Base):
    __tablename__ = 'events'
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String(255))
    start_date = sqla.Column(sqla.String(50))
    end_date = sqla.Column(sqla.String(50))
    sponsor = sqla.Column(sqla.String(255))
    season = sqla.Column(sqla.Integer)
    type = sqla.Column(sqla.String(50))
    num = sqla.Column(sqla.Integer)
    venue = sqla.Column(sqla.String(255))
    city = sqla.Column(sqla.String(255))
    country = sqla.Column(sqla.String(255))
    discipline = sqla.Column(sqla.String(50))
    main = sqla.Column(sqla.Integer)
    sex = sqla.Column(sqla.String(10))
    age_group = sqla.Column(sqla.String(10))
    url = sqla.Column(sqla.Text)
    related = sqla.Column(sqla.String(50))
    stage = sqla.Column(sqla.String(10))
    value_type = sqla.Column(sqla.String(50))
    short_name = sqla.Column(sqla.String(255))
    world_snooker_id = sqla.Column(sqla.Integer)
    ranking_type = sqla.Column(sqla.String(50))
    event_prediction_id = sqla.Column(sqla.Integer)
    team = sqla.Column(sqla.Boolean)
    format = sqla.Column(sqla.Integer)
    twitter = sqla.Column(sqla.String(255))
    hash_tag = sqla.Column(sqla.String(255))
    conversion_rate = sqla.Column(sqla.Float)
    all_rounds_added = sqla.Column(sqla.Boolean)
    photo_urls = sqla.Column(sqla.Text)
    num_competitors = sqla.Column(sqla.Integer)
    num_upcoming = sqla.Column(sqla.Integer)
    num_active = sqla.Column(sqla.Integer)
    num_results = sqla.Column(sqla.Integer)
    note = sqla.Column(sqla.Text)
    common_note = sqla.Column(sqla.Text)
    defending_champion = sqla.Column(sqla.Integer)
    previous_edition = sqla.Column(sqla.Integer)
    tour = sqla.Column(sqla.String(50))

    def __init__(self, event_data):
        self.id = event_data.ID
        self.name = event_data.Name
        self.start_date = event_data.StartDate
        self.end_date = event_data.EndDate
        self.sponsor = event_data.Sponsor
        self.season = event_data.Season
        self.type = event_data.Type
        self.num = event_data.Num
        self.venue = event_data.Venue
        self.city = event_data.City
        self.country = event_data.Country
        self.discipline = event_data.Discipline
        self.main = event_data.Main
        self.sex = event_data.Sex
        self.age_group = event_data.AgeGroup
        self.url = event_data.Url
        self.related = event_data.Related
        self.stage = event_data.Stage
        self.value_type = event_data.ValueType
        self.short_name = event_data.ShortName
        self.world_snooker_id = event_data.WorldSnookerId
        self.ranking_type = event_data.RankingType
        self.event_prediction_id = event_data.EventPredictionID
        self.team = event_data.Team
        self.format = event_data.Format
        self.twitter = event_data.Twitter
        self.hash_tag = event_data.HashTag
        self.conversion_rate = event_data.ConversionRate
        self.all_rounds_added = event_data.AllRoundsAdded
        self.photo_urls = event_data.PhotoURLs
        self.num_competitors = event_data.NumCompetitors
        self.num_upcoming = event_data.NumUpcoming
        self.num_active = event_data.NumActive
        self.num_results = event_data.NumResults
        self.note = event_data.Note
        self.common_note = event_data.CommonNote
        self.defending_champion = event_data.DefendingChampion
        self.previous_edition = event_data.PreviousEdition
        self.tour = event_data.Tour

class Round(Base):
    __tablename__ = 'rounds'
    id = sqla.Column(sqla.Integer, primary_key=True, autoincrement=True)
    round = sqla.Column(sqla.Integer)
    round_name = sqla.Column(sqla.String(255))
    event_id = sqla.Column(sqla.Integer)
    main_event = sqla.Column(sqla.Integer)
    distance = sqla.Column(sqla.Integer)
    num_left = sqla.Column(sqla.Integer)
    num_matches = sqla.Column(sqla.Integer)
    note = sqla.Column(sqla.Text)
    value_type = sqla.Column(sqla.String(50))
    rank = sqla.Column(sqla.Integer)
    money = sqla.Column(sqla.Float)
    seed_gets_half = sqla.Column(sqla.Integer)
    actual_money = sqla.Column(sqla.Float)
    currency = sqla.Column(sqla.String(10))
    conversion_rate = sqla.Column(sqla.Float)
    points = sqla.Column(sqla.Integer)
    seed_points = sqla.Column(sqla.Integer)

    def __init__(self, round_data):
        self.round = round_data.Round
        self.round_name = round_data.RoundName
        self.event_id = round_data.EventID
        self.main_event = round_data.MainEvent
        self.distance = round_data.Distance
        self.num_left = round_data.NumLeft
        self.num_matches = round_data.NumMatches
        self.note = round_data.Note
        self.value_type = round_data.ValueType
        self.rank = round_data.Rank
        self.money = round_data.Money
        self.seed_gets_half = round_data.SeedGetsHalf
        self.actual_money = round_data.ActualMoney
        self.currency = round_data.Currency
        self.conversion_rate = round_data.ConversionRate
        self.points = round_data.Points
        self.seed_points = round_data.SeedPoints

def init_db():
    Base.metadata.create_all(engine)

def fetch_single_event(event_data, client=None, session=None, max_retries=2):
    """
    Fetch and store a single event's information and its rounds.

    Args:
        event_data: Event object from API
        client: Optional API client instance
        session: Optional database session instance
        max_retries: Maximum retry attempts on failure

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

    event_id = event_data.ID
    
    for attempt in range(max_retries):
        try:
            print(f"Fetching event {event_id} (attempt {attempt + 1}/{max_retries})...")

            # Create or update event in database
            event = Event(event_data)
            session.merge(event)  # merge will insert or update
            session.commit()

            print(f"Successfully stored/updated event {event_id}: {event_data.Name}")

            # Fetch and store rounds for this event
            try:
                rounds = client.round_info_by_event(event_id)
                for round_data in rounds:
                    round_obj = Round(round_data)
                    session.merge(round_obj)  # merge will insert or update
                session.commit()

                print(f"Successfully stored {len(rounds)} rounds for event {event_id}")
            except Exception as e:
                print(f"Warning: Failed to fetch rounds for event {event_id}: {type(e).__name__}")
                # Continue anyway - event data was stored successfully
            
            return True

        except Exception as e:
            error_name = type(e).__name__
            print(f"Error fetching/storing event {event_id} (attempt {attempt + 1}/{max_retries}): {error_name}")
            session.rollback()
            
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch event {event_id} after {max_retries} attempts. Skipping.")
                return False

    if should_close_session:
        session.close()
    
    return False

def fetch_and_store_events(season=None):
    """
    Fetch and store all events for a given season and their rounds.

    Args:
        season (int): The season year to fetch events for
    """
    # Initialize API client
    client = SnookerOrgApi(headers={'X-Requested-By': api_config['x_requested_by']})
    if season is None:
        season = get_current_season()
    # Get events for the season
    events = client.season_events(season)
    print(f"Found {len(events)} events for season {season}")

    # Create database session
    DBSession = sqla.orm.sessionmaker(bind=engine)
    session = DBSession()

    # Process each event
    for i, event_data in enumerate(events):
        success = fetch_single_event(event_data, client=client, session=session)
        if not success:
            continue

        # Wait between requests (except for the last one)
        if i < len(events) - 1:
            wait_time = int(api_config['request_delay_seconds'])
            print(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)

    session.close()
    print("Finished fetching all events and rounds")

if __name__ == '__main__':
    init_db()

    # Fetch events for season 2025
    fetch_and_store_events(2025)