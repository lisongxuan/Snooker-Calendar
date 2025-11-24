import os
import configparser
import time
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from player_matches_to_ics import generate_player_calendar
from query_data import query_all_ranking_players
def load_config(filename='config.txt'):
    config = configparser.ConfigParser()
    config.read(filename)

    # Load database configuration
    db_config = {key: value for key, value in config['database'].items()}

    # Load API configuration
    api_config = {key: value for key, value in config['api'].items()}

    return db_config, api_config
db_config, api_config = load_config()

# Create SQLAlchemy engine
engine = sqla.create_engine(f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}", pool_size=10, max_overflow=-1)
Base = declarative_base()
class IcsLastUpdated(Base):
    __tablename__ = 'icslastupdated'
    playerid = sqla.Column(sqla.Integer, primary_key=True)
    lastupdated = sqla.Column(sqla.DateTime)

    def __init__(self, pid, lastupdated):
        self.playerid = pid
        self.lastupdated = lastupdated

def init_db():
    Base.metadata.create_all(engine)

def update_ics_last_updated(player_id, timestamp):
    Session = sessionmaker(bind=engine)
    session = Session()
    record = session.query(IcsLastUpdated).filter_by(playerid=player_id).first()
    if record:
        record.lastupdated = timestamp
    else:
        record = IcsLastUpdated(player_id, timestamp)
        session.add(record)
    session.commit()
    session.close()

def generate_all_players_calendars(year=None):
    """
    为所有活跃玩家生成ICS日历文件
    
    Args:
        year (int): 目标年份，默认当前年份
    """
    if year is None:
        year = datetime.now().year
    
    # 创建输出目录
    output_dir = f"ics_calendars"
    os.makedirs(output_dir, exist_ok=True)

    players = query_all_ranking_players()

    if not players:
        print("No ranking players found or error occurred")
        return

    success_count = 0
    total_count = len(players)

    for i, player in enumerate(players, 1):
        # New shape: merged dict with player fields and ranking fields
        player_id = player.get('player_id')

        firstname = player.get('firstname')
        lastname = player.get('lastname')
        surname_first = player.get('surname_first')

        if firstname or lastname:
            if surname_first:
                player_name = f"{lastname or ''} {firstname or ''}".strip()
            else:
                player_name = f"{firstname or ''} {lastname or ''}".strip()
        else:
            print(f"[{i}/{total_count}] Skipping player ID: {player_id} due to missing name info")
            continue
        print(f"[{i}/{total_count}] Generating calendar for {player_name} (ID: {player_id})...")
        
        try:
            ics_content = generate_player_calendar(player_id, year)
            
            if ics_content:
                filename = f"{player_id}.ics"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(ics_content)

                update_ics_last_updated(player_id, datetime.now())
                success_count += 1
                print(f"✓ Saved: {filepath}")
            else:
                print(f"⚠ No matches found for {player_name}")
            wait_time = int(api_config['request_delay_seconds'])
            print(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"✗ Error generating calendar for {player_name}: {e}")
            continue
    
    print(f"\nCompleted: {success_count}/{total_count} calendars generated successfully")

if __name__ == '__main__':
    init_db()
    generate_all_players_calendars()