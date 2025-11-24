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
from datetime import datetime, date, timezone
import time
import threading

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
    """Return True if the given info has NOT been updated today."""
    Session = sessionmaker(bind=engine)
    session = Session()
    record = session.query(InfoLastUpdated).filter_by(info=info_name).first()
    session.close()
    if not record or not record.lastupdated:
        return True
    # compare dates using UTC/GMT date
    # record.lastupdated is stored in UTC (see update_last_updated)
    return record.lastupdated.date() != datetime.utcnow().date()

# Global re-entrant lock to ensure only one job runs at a time
job_lock = threading.RLock()

def update_rankings_job():
    with job_lock:
        logger.info("Starting rankings update...")
        try:
            fetch_and_store_players()
            # store UTC timestamp
            update_last_updated("players", datetime.utcnow())
            logger.info("Rankings update completed successfully")
        except Exception as e:
            logger.error(f"Rankings update failed: {e}")

def generate_ics_job():
    with job_lock:
        logger.info("Starting ICS generation...")
        try:
            generate_all_players_calendars()
            logger.info("ICS generation completed successfully")
        except Exception as e:
            logger.error(f"ICS generation failed: {e}")

        # After generating ICS, opportunistically run the daily updates if they haven't run yet
        try:
            # Use UTC/GMT for opportunistic window
            now = datetime.utcnow()
            # GMT 02:00-05:00 window preference (change if you need a specific TZ)
            if 2 <= now.hour < 5:
                if needs_update_today("events"):
                    logger.info("Within preferred window — running event info update")
                    update_event_info_job()
                if needs_update_today("players"):
                    logger.info("Within preferred window — running rankings update")
                    update_rankings_job()
        except Exception as e:
            logger.error(f"Error while checking/triggering opportunistic updates: {e}")

def update_event_info_job():
    with job_lock:
        logger.info("Starting event info update...")
        try:
            fetch_and_store_events()
            # store UTC timestamp
            update_last_updated("events", datetime.utcnow())
            logger.info("Event info update completed successfully")
        except Exception as e:
            logger.error(f"Event info update failed: {e}")

def main():
    # Run scheduler in UTC/GMT
    scheduler = BlockingScheduler(timezone=timezone.utc)
    # interval for continuous ICS generation (minutes). Make configurable via config.txt if desired.
    try:
        generate_interval = int(db_config.get('generate_interval_minutes', 15))
    except Exception:
        generate_interval = 15

    # Run generate_ics_job continuously on an interval
    scheduler.add_job(
        generate_ics_job,
        trigger='interval',
        minutes=generate_interval,
        id='continuous_ics_generation',
        name='Continuous ICS Generation',
        # schedule first run immediately using UTC
        next_run_time=datetime.now(timezone.utc)
    )

    # Add fallback daily cron jobs (05:10) to guarantee each update runs at least once per day
    # They check "needs_update_today" internally so they'll be no-ops if already run.
    scheduler.add_job(
        update_event_info_job,
        trigger=CronTrigger(hour=5, minute=10, timezone=timezone.utc),
        id='daily_event_info_fallback',
        name='Daily Event Info Fallback'
    )

    scheduler.add_job(
        update_rankings_job,
        trigger=CronTrigger(hour=5, minute=40, timezone=timezone.utc),
        id='daily_rankings_fallback',
        name='Daily Rankings Fallback'
    )
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    for j in scheduler.get_jobs():
        # Prefer the Job attribute if present, otherwise ask the trigger for next fire time.
        next_run = getattr(j, 'next_run_time', None)
        if next_run is None:
            try:
                # ask trigger for next fire time relative to now (use UTC)
                next_run = j.trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            except Exception:
                next_run = None
        logger.info(f"Job {j.id} next run at {next_run}")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == '__main__':
    # basic logger setup
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger(__name__)
    
    init_db()
    main()