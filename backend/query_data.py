import configparser
import datetime
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
engine = sqla.create_engine(
    f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
    pool_size=10,
    max_overflow=-1,
    pool_pre_ping=True,
    pool_recycle=3600,
)
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

class Round(Base):
    __tablename__ = 'rounds'
    round = sqla.Column(sqla.Integer, primary_key=True)
    round_name = sqla.Column(sqla.String(255))
    event_id = sqla.Column(sqla.Integer, primary_key=True)
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

class Ranking(Base):
    __tablename__ = 'rankings'
    position = sqla.Column(sqla.Integer, primary_key=True)
    player_id = sqla.Column(sqla.Integer)
    sum_value = sqla.Column(sqla.Float)

class IcsLastUpdated(Base):
    __tablename__ = 'icslastupdated'
    playerid = sqla.Column(sqla.Integer, primary_key=True)
    lastupdated = sqla.Column(sqla.DateTime)
class InfoLastUpdated(Base):
    __tablename__ = 'infolastupdated'
    info = sqla.Column(sqla.String(255), primary_key=True)
    lastupdated = sqla.Column(sqla.DateTime)

# Create session factory
DBSession = sessionmaker(bind=engine)

def query_player_info(player_id):
    """
    根据 player_id 查询运动员信息

    Args:
        player_id (int): 运动员ID

    Returns:
        dict: 包含 type, firstname, lastname, surname_first, nationality, born, num_ranking_titles 的字典
              如果查询失败或不存在，返回 None
    """
    session = DBSession()
    try:
        player = session.query(Player).filter(Player.id == player_id).first()
        if player:
            return {
                'type': player.type,
                'firstname': player.first_name,
                'lastname': player.last_name,
                'surname_first': player.surname_first,
                'nationality': player.nationality,
                'born': player.born,
                'num_ranking_titles': player.num_ranking_titles
            }
        else:
            return None
    except Exception as e:
        print(f"Error querying player {player_id}: {e}")
        return None
    finally:
        session.close()

def query_event_info(event_id):
    """
    根据 event_id 查询赛事信息

    Args:
        event_id (int): 赛事ID

    Returns:
        dict: 包含 name, start_date, end_date, season, type, venue, city, country, sex, age_group, url, stage, ranking_type, defending_champion 的字典
              如果查询失败或不存在，返回 None
    """
    session = DBSession()
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if event:
            return {
                'name': event.name,
                'start_date': event.start_date,
                'end_date': event.end_date,
                'season': event.season,
                'type': event.type,
                'venue': event.venue,
                'city': event.city,
                'country': event.country,
                'sex': event.sex,
                'age_group': event.age_group,
                'url': event.url,
                'stage': event.stage,
                'ranking_type': event.ranking_type,
                'defending_champion': event.defending_champion
            }
        else:
            return None
    except Exception as e:
        print(f"Error querying event {event_id}: {e}")
        return None
    finally:
        session.close()

def query_round_info(event_id, round_num):
    """
    根据 event_id 和 round 查询轮次信息

    Args:
        event_id (int): 赛事ID
        round_num (int): 轮次编号

    Returns:
        dict: 包含 round_name, main_event, note, value_type, rank, money, seed_gets_half, actual_money, currency 的字典
              如果查询失败或不存在，返回 None
    """
    session = DBSession()
    try:
        round_info = session.query(Round).filter(
            Round.event_id == event_id,
            Round.round == round_num
        ).first()
        if round_info:
            return {
                'round_name': round_info.round_name,
                'distance': round_info.distance,
                'main_event': round_info.main_event,
                'note': round_info.note,
                'value_type': round_info.value_type,
                'rank': round_info.rank,
                'money': round_info.money,
                'seed_gets_half': round_info.seed_gets_half,
                'actual_money': round_info.actual_money,
                'currency': round_info.currency
            }
        else:
            return None
    except Exception as e:
        print(f"Error querying round for event {event_id}, round {round_num}: {e}")
        return None
    finally:
        session.close()

def query_player_ranking(player_id):
    """
    根据 player_id 查询运动员排名信息

    Args:
        player_id (int): 运动员ID

    Returns:
        dict: 包含 position, sum_value 的字典
              如果查询失败或不存在，返回 None
    """
    session = DBSession()
    try:
        ranking = session.query(Ranking).filter(Ranking.player_id == player_id).first()
        if ranking:
            return {
                'position': ranking.position,
                'sum_value': ranking.sum_value
            }
        else:
            return None
    except Exception as e:
        print(f"Error querying ranking for player {player_id}: {e}")
        return None
    finally:
        session.close()
def query_all_ranking_players(page=1, limit=-1, search=None):
    """
        查询所有有排名的球员
    """
    session = DBSession()
    try:
        if search:
            search_pattern = f"%{search}%"
            if limit > 0:
                results = session.query(Ranking, Player, IcsLastUpdated).outerjoin(
                    Player, Player.id == Ranking.player_id
                ).outerjoin(
                    IcsLastUpdated, IcsLastUpdated.playerid == Ranking.player_id
                ).filter(
                    sqla.or_(
                        Player.first_name.ilike(search_pattern),
                        Player.last_name.ilike(search_pattern)
                    )
                ).limit(limit).offset((page - 1) * limit).all()
            else:
                results = session.query(Ranking, Player, IcsLastUpdated).outerjoin(
                    Player, Player.id == Ranking.player_id
                ).outerjoin(
                    IcsLastUpdated, IcsLastUpdated.playerid == Ranking.player_id
                ).filter(
                    sqla.or_(
                        Player.first_name.ilike(search_pattern),
                        Player.last_name.ilike(search_pattern)
                    )
                ).all()
        else:
            if limit > 0:
                results = session.query(Ranking, Player, IcsLastUpdated).outerjoin(
                Player, Player.id == Ranking.player_id
                ).outerjoin(
                IcsLastUpdated, IcsLastUpdated.playerid == Ranking.player_id
                ).limit(limit).offset((page - 1) * limit).all()
            else:
                results = session.query(Ranking, Player, IcsLastUpdated).outerjoin(
                Player, Player.id == Ranking.player_id
                ).outerjoin(
                IcsLastUpdated, IcsLastUpdated.playerid == Ranking.player_id
                ).all()
        players = []
        for ranking, player, ics in results:
            # Build a merged dict with the fields the caller expects.
            players.append({
                'type': getattr(player, 'type', None) if player is not None else None,
                'firstname': getattr(player, 'first_name', None) if player is not None else None,
                'lastname': getattr(player, 'last_name', None) if player is not None else None,
                'surname_first': getattr(player, 'surname_first', None) if player is not None else None,
                'nationality': getattr(player, 'nationality', None) if player is not None else None,
                'born': getattr(player, 'born', None) if player is not None else None,
                'num_ranking_titles': getattr(player, 'num_ranking_titles', None) if player is not None else None,
                'position': ranking.position,
                'player_id': ranking.player_id,
                'sum_value': ranking.sum_value,
                'last_updated': ics.lastupdated if ics is not None else None
            })

        return players
    except Exception as e:
        print(f"Error querying ranking: {type(e).__name__}: {e}")
        raise
    finally:
        session.close()

def query_info_last_updated():
    session = DBSession()
    try:
        result = session.query(InfoLastUpdated).all()
        return result
    except Exception as e:
        print(f"Error querying info last updated: {type(e).__name__}: {e}")
        raise
    finally:
        session.close()


_current_season_cache = {"value": None, "ts": 0}
_SEASON_CACHE_TTL = 86400  # 24 hours


def get_current_season(retries: int = 3, backoff_factor: float = 1.0, status_forcelist=(429, 500, 502, 503, 504)):
    """缓存包装器：结果缓存 24 小时，避免每次请求都调用外部 API。"""
    now = time.time()
    if _current_season_cache["value"] is not None and now - _current_season_cache["ts"] < _SEASON_CACHE_TTL:
        return _current_season_cache["value"]

    result = _fetch_current_season(retries, backoff_factor, status_forcelist)
    if result is not None:
        _current_season_cache["value"] = result
        _current_season_cache["ts"] = now
    return result


def _fetch_current_season(retries: int = 3, backoff_factor: float = 1.0, status_forcelist=(429, 500, 502, 503, 504)):
    """
    从 https://api.snooker.org/?t=20 获取当前赛季（CurrentSeason）。

    使用 `api_config['x_requested_by']` 设置请求头 `X-Requested-By`。
    返回 CurrentSeason 的整数值，如果请求失败或未找到返回 None。
    """
    url = 'https://api.snooker.org/?t=20'
    headers = {}
    try:
        # api_config 来自模块顶部的 load_config
        x_req = api_config.get('x_requested_by') if isinstance(api_config, dict) else None
        if x_req:
            headers['X-Requested-By'] = x_req
    except Exception:
        # 忽略, headers 保持为空
        pass

    # Build a requests Session with retry policy
    session = requests.Session()
    try:
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=frozenset(["GET", "HEAD"])
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # 期望返回像 [{"CurrentSeason": 2024}]
        if isinstance(data, list) and len(data) > 0:
            return data[0].get('CurrentSeason')
        elif isinstance(data, dict):
            return data.get('CurrentSeason')
        else:
            return None
    except Exception as e:
        # If Retry-based adapter isn't available or raises, fallback to manual retry loop
        try:
            # print a debug/log message indicating fallback to manual retries
            print(f"Primary request failed or retry adapter error, fallback manual retry: {e}")
            for attempt in range(1, retries + 1):
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get('CurrentSeason')
                    elif isinstance(data, dict):
                        return data.get('CurrentSeason')
                    else:
                        return datetime.now().year 
                except Exception as inner_e:
                    # If it's the last attempt, raise
                    if attempt == retries:
                        print(f"Final attempt failed: {inner_e}")
                        return datetime.now().year
                    # Sleep with exponential backoff before next attempt
                    sleep_time = backoff_factor * (2 ** (attempt - 1))
                    print(f"Retry {attempt}/{retries} failed: {inner_e}. Sleeping {sleep_time}s before next attempt.")
                    time.sleep(sleep_time)
        except Exception as inner_fallback_e:
            print(f"Fallback retry mechanism failed: {inner_fallback_e}")
            return datetime.now().year
    finally:
        try:
            session.close()
        except Exception:
            pass


if __name__ == '__main__':
    # Test the query functions
    print("Testing query functions...")

    # Query player info
    player_info = query_player_info(1)  # Assuming player with ID 1 exists
    if player_info:
        print(f"Player info: {player_info}")
    else:
        print("Player not found or error occurred")

    # Query event info
    event_info = query_event_info(1)  # Assuming event with ID 1 exists
    if event_info:
        print(f"Event info: {event_info}")
    else:
        print("Event not found or error occurred")

    # Query round info
    round_info = query_round_info(1, 1)  # Assuming event 1, round 1 exists
    if round_info:
        print(f"Round info: {round_info}")
    else:
        print("Round not found or error occurred")

    # Query current season from API
    current_season = get_current_season()
    if current_season is not None:
        print(f"CurrentSeason from API: {current_season}")
    else:
        print("Could not fetch CurrentSeason from API")


