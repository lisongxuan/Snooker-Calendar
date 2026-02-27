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
engine = sqla.create_engine(
    f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
    pool_size=10,
    max_overflow=-1,
    pool_pre_ping=True,
    pool_recycle=3600,
)
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
    为所有活跃玩家生成ICS日历文件。
    当出现错误时自动重试，重试失败则跳过该玩家，不阻塞整体进程。
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
    skip_count = 0
    total_count = len(players)
    
    # 设置每个玩家的超时时间（秒）- 增加到90秒以应对网络延迟
    per_player_timeout = 90

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
            print(f"[{i}/{total_count}] ⊘ Skipping player ID: {player_id} (missing name)")
            skip_count += 1
            continue
            
        print(f"[{i}/{total_count}] [{datetime.now().strftime('%H:%M:%S')}] Processing {player_name} (ID: {player_id})...")
        
        try:
            # 使用多进程实现超时
            with multiprocessing.Pool(1) as pool:
                result = pool.apply_async(generate_player_calendar_with_timeout, 
                                         (player_id, year, per_player_timeout))
                
                try:
                    # 等待结果，设置超时（添加10秒缓冲）
                    ics_content = result.get(timeout=per_player_timeout + 10)
                    
                    if ics_content:
                        filename = f"{player_id}.ics"
                        filepath = os.path.join(output_dir, filename)
                        
                        try:
                            with open(filepath, 'wb') as f:
                                f.write(ics_content)
                            update_ics_last_updated(player_id, datetime.now())
                            success_count += 1
                            print(f"  ✓ Saved ({len(ics_content)} bytes)")
                        except Exception as write_err:
                            print(f"  ✗ Failed to save file: {type(write_err).__name__}")
                            skip_count += 1
                    else:
                        print(f"  ⊘ No matches found or API failed after retries")
                        skip_count += 1
                        
                except multiprocessing.TimeoutError:
                    print(f"  ✗ Process timeout ({per_player_timeout}s exceeded) - terminating and skipping")
                    skip_count += 1
                    try:
                        pool.terminate()
                        pool.join(timeout=5)
                    except Exception as term_err:
                        print(f"  Warning: Error terminating pool: {type(term_err).__name__}")
                except Exception as pool_err:
                    print(f"  ✗ Process error ({type(pool_err).__name__}) - skipping")
                    skip_count += 1
                    try:
                        pool.terminate()
                        pool.join(timeout=5)
                    except Exception as term_err:
                        print(f"  Warning: Error terminating pool: {type(term_err).__name__}")
                    
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__} - skipping")
            skip_count += 1
        
        # 添加延迟避免API限制
        wait_time = int(api_config.get('request_delay_seconds', 1))
        if i < total_count:  # 不在最后一个后面等待
            time.sleep(wait_time)
    
    print(f"\n{'='*60}")
    print(f"Batch Generation Complete:")
    print(f"  Success: {success_count}/{total_count}")
    print(f"  Skipped: {skip_count}/{total_count}")
    print(f"{'='*60}")
    
if __name__ == '__main__':
    init_db()
    generate_all_players_calendars()