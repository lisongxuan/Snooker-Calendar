# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from fetch_events import fetch_and_store_events
from fetch_players import fetch_and_store_players
from batch_ics_generator import generate_all_players_calendars
import configparser
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import threading

# ------------------------------------------------------------------
# 配置加载
# ------------------------------------------------------------------
def load_config(filename='config.txt'):
    config = configparser.ConfigParser()
    config.read(filename)
    db_config = {key: value for key, value in config['database'].items()}
    api_config = {key: value for key, value in config['api'].items()}
    return db_config, api_config

db_config, api_config = load_config()

engine = sqla.create_engine(
    f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
    pool_size=10,
    max_overflow=-1,
    pool_pre_ping=True,
    pool_recycle=3600,
)
Base = declarative_base()

class InfoLastUpdated(Base):
    __tablename__ = 'infolastupdated'
    info = sqla.Column(sqla.String(255), primary_key=True)
    lastupdated = sqla.Column(sqla.DateTime)

    def __init__(self, info, lastupdated):
        self.info = info
        self.lastupdated = lastupdated

def init_db():
    Base.metadata.create_all(engine)

def update_last_updated(info_name, timestamp):
    Session = sessionmaker(bind=engine)
    session = Session()
    record = session.query(InfoLastUpdated).filter_by(info=info_name).first()
    if record:
        record.lastupdated = timestamp
    else:
        record = InfoLastUpdated(info_name, timestamp)
        session.add(record)
    session.commit()
    session.close()

def needs_update_today(info_name):
    """Return True if the given info has NOT been updated today (UTC)."""
    Session = sessionmaker(bind=engine)
    session = Session()
    record = session.query(InfoLastUpdated).filter_by(info=info_name).first()
    session.close()
    if not record or not record.lastupdated:
        return True
    return record.lastupdated.date() != datetime.utcnow().date()

# ------------------------------------------------------------------
# 维护窗口: 北京时间 10:00-15:00 == UTC 02:00-07:00
# 窗口内只允许 events/rankings 更新；ICS 生成让路
# ------------------------------------------------------------------
MAINTENANCE_START_HOUR_UTC = 2
MAINTENANCE_END_HOUR_UTC = 7

def in_maintenance_window(now_utc=None):
    now_utc = now_utc or datetime.utcnow()
    return MAINTENANCE_START_HOUR_UTC <= now_utc.hour < MAINTENANCE_END_HOUR_UTC

# 维护窗口内 events/rankings 的每日尝试时刻 (UTC)。一天最多 3 次，已成功则 no-op
MAINTENANCE_ATTEMPT_TIMES_UTC = [(2, 10), (4, 10), (6, 10)]

# ------------------------------------------------------------------
# 全局任务锁与取消标志（取消都是协作式的，等待均有界）
# ------------------------------------------------------------------
job_lock = threading.RLock()
running_job_type = None
cancel_flags = {
    'rankings': threading.Event(),
    'events': threading.Event(),
    'ics': threading.Event(),
    'maintenance': threading.Event(),
}

def should_cancel(job_type):
    return cancel_flags[job_type].is_set()

def clear_cancel_flag(job_type):
    cancel_flags[job_type].clear()

def set_cancel_flag(job_type):
    cancel_flags[job_type].set()

def acquire_job_preemptively(job_type, timeout=600):
    """
    请求任务锁（等待时间有界）。若其它任务在运行，先设置其取消标志，
    等它在下个检查点让出锁。
    """
    global running_job_type
    if running_job_type and running_job_type != job_type:
        logger.info(f"Cancelling {running_job_type} job to run {job_type} job")
        set_cancel_flag(running_job_type)
    acquired = job_lock.acquire(timeout=timeout)
    if acquired:
        running_job_type = job_type
        clear_cancel_flag(job_type)
        return True
    logger.warning(f"Could not acquire lock to run {job_type} job within {timeout}s timeout")
    return False

def release_job():
    global running_job_type
    running_job_type = None
    job_lock.release()

# ------------------------------------------------------------------
# events / rankings（仅在维护窗口内由 maintenance_sync_job 调用）
# ------------------------------------------------------------------
def update_events_once():
    """单次 events 更新；成功才写时间戳；异常向上抛（本次尝试失败，留待后续尝试）。"""
    logger.info("Starting event info update...")
    start_time = datetime.utcnow()
    fetch_and_store_events()
    update_last_updated("events", datetime.utcnow())
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Event info update completed successfully in {duration:.1f} seconds")

def update_rankings_once():
    """单次 rankings/players 更新；同上。"""
    logger.info("Starting rankings update...")
    start_time = datetime.utcnow()
    fetch_and_store_players()
    update_last_updated("players", datetime.utcnow())
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Rankings update completed successfully in {duration:.1f} seconds")

def maintenance_sync_job():
    """维护窗口内顺序执行 events -> rankings（每项独立 try，一项失败不影响另一项）。"""
    if not in_maintenance_window():
        logger.info("Maintenance job fired outside maintenance window - no-op")
        return
    if not acquire_job_preemptively('maintenance', timeout=600):
        return
    try:
        if should_cancel('maintenance'):
            return
        if needs_update_today('events'):
            try:
                update_events_once()
            except Exception as e:
                logger.error(f"Event info update failed: {e}", exc_info=True)
        else:
            logger.info("events already updated today - skip")

        if should_cancel('maintenance'):
            return
        if needs_update_today('players'):
            try:
                update_rankings_once()
            except Exception as e:
                logger.error(f"Rankings update failed: {e}", exc_info=True)
        else:
            logger.info("players already updated today - skip")
    finally:
        release_job()

# ------------------------------------------------------------------
# ICS 生成（维护窗口内跳过；可被维护任务协作式抢占）
# ------------------------------------------------------------------
def generate_ics_job():
    if in_maintenance_window():
        logger.info(
            f"Maintenance window (UTC {MAINTENANCE_START_HOUR_UTC:02d}-{MAINTENANCE_END_HOUR_UTC:02d}); skip ICS generation run"
        )
        return
    if not acquire_job_preemptively('ics'):
        return
    try:
        if should_cancel('ics'):
            logger.info("ICS generation cancelled")
            return
        logger.info("Starting ICS generation...")
        start_time = datetime.utcnow()
        generate_all_players_calendars(cancel_check=lambda: should_cancel('ics'))
        if should_cancel('ics'):
            logger.info("ICS generation cancelled mid-run (maintenance taking over)")
            return
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"ICS generation completed successfully in {duration:.1f} seconds")
    except Exception as e:
        logger.error(f"ICS generation failed: {e}", exc_info=True)
    finally:
        release_job()

# ------------------------------------------------------------------
# 调度入口
# ------------------------------------------------------------------
def main():
    scheduler = BlockingScheduler(timezone=timezone.utc)
    try:
        generate_interval = int(db_config.get('generate_interval_minutes', 15))
    except Exception:
        generate_interval = 15

    # ICS: 30 分钟间隔触发，但维护窗口内直接跳过
    scheduler.add_job(
        generate_ics_job,
        trigger='interval',
        minutes=generate_interval,
        id='continuous_ics_generation',
        name='Continuous ICS Generation',
        next_run_time=datetime.now(timezone.utc),
        max_instances=1,
        coalesce=True,
    )

    # 维护窗口内 events/rankings: 每天最多 3 次有界尝试 (UTC 02:10 / 04:10 / 06:10)
    for (hh, mm) in MAINTENANCE_ATTEMPT_TIMES_UTC:
        scheduler.add_job(
            maintenance_sync_job,
            trigger=CronTrigger(hour=hh, minute=mm, timezone=timezone.utc),
            id=f'maintenance_sync_{hh:02d}{mm:02d}',
            name=f'Maintenance Sync (UTC {hh:02d}:{mm:02d})',
            max_instances=1,
            coalesce=True,
        )

    logger.info(
        f"Scheduler started. Maintenance window UTC {MAINTENANCE_START_HOUR_UTC:02d}-"
        f"{MAINTENANCE_END_HOUR_UTC:02d} (= Beijing 10:00-15:00): only events/rankings run inside. Ctrl+C to exit."
    )
    for j in scheduler.get_jobs():
        next_run = getattr(j, 'next_run_time', None)
        if next_run is None:
            try:
                next_run = j.trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            except Exception:
                next_run = None
        logger.info(f"Job {j.id} next run at {next_run}")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger(__name__)

    init_db()
    main()
