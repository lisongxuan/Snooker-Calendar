#batch_ics_generator.py
import os
import configparser
import time
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from player_matches_to_ics import generate_player_calendar
from query_data import query_all_ranking_players,get_current_season
import multiprocessing
import time



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

# batch_ics_generator.py
import multiprocessing
import time

def generate_player_calendar_with_timeout(player_id, year, timeout):
    """在独立进程中运行生成日历的函数"""
    from player_matches_to_ics import generate_player_calendar
    return generate_player_calendar(player_id, year)

def generate_all_players_calendars(year=None):
    """
    为所有活跃玩家生成ICS日历文件
    """
    if year is None:
        from query_data import get_current_season
        year = get_current_season()
    
    # 创建输出目录
    output_dir = f"ics_calendars"
    os.makedirs(output_dir, exist_ok=True)

    players = query_all_ranking_players()

    if not players:
        print("No ranking players found or error occurred")
        return

    success_count = 0
    total_count = len(players)
    
    # 设置每个玩家的超时时间（秒）
    per_player_timeout = 300  # 5分钟

    for i, player in enumerate(players, 1):
        player_id = player.get('player_id')
        
        # 处理玩家姓名
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
            # 使用多进程实现超时
            with multiprocessing.Pool(1) as pool:
                result = pool.apply_async(generate_player_calendar_with_timeout, 
                                         (player_id, year, per_player_timeout))
                
                try:
                    # 等待结果，设置超时
                    ics_content = result.get(timeout=per_player_timeout)
                    
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
                        
                except multiprocessing.TimeoutError:
                    print(f"✗ Timeout generating calendar for {player_name} (ID: {player_id}) after {per_player_timeout} seconds")
                    # 终止进程
                    pool.terminate()
                    pool.join()
                    continue
                    
        except Exception as e:
            print(f"✗ Error generating calendar for {player_name}: {e}")
            # 记录详细错误信息以便调试
            import traceback
            traceback.print_exc()
            continue
        
        # 添加延迟避免API限制
        wait_time = int(api_config.get('request_delay_seconds', 1))
        print(f"Waiting {wait_time} seconds...")
        time.sleep(wait_time)
    
    print(f"\nCompleted: {success_count}/{total_count} calendars generated successfully")
    
if __name__ == '__main__':
    init_db()
    generate_all_players_calendars()