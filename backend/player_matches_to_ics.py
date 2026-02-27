#!/usr/bin/env python3
"""
Script to convert snooker player matches to ICS calendar format
"""
import configparser
import sys
import time
from datetime import datetime, timedelta
from snooker.api import SnookerOrgApi
from icalendar import Calendar, Event, vText
import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from query_data import query_player_info, query_event_info, query_round_info, query_player_ranking
from fetch_players import fetch_single_player
def load_config(filename='config.txt'):
    config = configparser.ConfigParser()
    config.read(filename)

    # Load database configuration
    db_config = {key: value for key, value in config['database'].items()}

    # Load API configuration
    api_config = {key: value for key, value in config['api'].items()}

    return db_config, api_config
db_config, api_config = load_config()

def get_player_info(player_id):
    """Get player info from database, fetching from API if needed"""
    try:
        player_info = query_player_info(player_id)
        if not player_info:
            # Timeout for single player fetch is 10 seconds
            fetch_single_player(player_id)
        player_info = query_player_info(player_id)
        return player_info
    except Exception as e:
        print(f"  Warning - Failed to get player info for {player_id}: {type(e).__name__}")
        return None

def create_match_event(match, player_id):
    """
    Create an ICS event for a single match

    Args:
        match: Match object from the API
        player_id: The player ID we're generating calendar for

    Returns:
        Event: ICS calendar event
    """
    event = Event()

    # Query additional information
    player1_info = get_player_info(match.Player1ID)
    player2_info = get_player_info(match.Player2ID)
    event_info = query_event_info(match.EventID)
    round_info = query_round_info(match.EventID, match.Round)

    # Check if this is a future match
    is_future_match = match.WinnerID==0
    # Format player names
    def format_player_name(player_info, player_id):
        if player_info:
            if player_info.get('surname_first', False):
                return f"{player_info['lastname']}, {player_info['firstname']}"
            else:
                return f"{player_info['firstname']} {player_info['lastname']}"
        return f"Player {player_id}"

    player1_name = format_player_name(player1_info, match.Player1ID)
    player2_name = format_player_name(player2_info, match.Player2ID)

    # Format event name
    event_name = event_info['name'] if event_info else f"Event {match.EventID}"

    # Format round name
    round_name = round_info['round_name'] if round_info else f"Round {match.Round}"

    # Create summary/title with player names and event info
    summary_parts = [
        f"{player1_name} vs {player2_name}",
        f"{match.Score1} - {match.Score2}",
        f"{event_name}",
        f"{round_name}"
    ]
    event.add('summary', ' | '.join(summary_parts))

    # Create description
    description_parts = []

    # Add player details
    if player1_info:
        description_parts.append(f"Player 1: {player1_name}")
        if player1_info.get('nationality'):
            description_parts.append(f"Nationality: {player1_info['nationality']}")
        if player1_info.get('born'):
            description_parts.append(f"Born: {player1_info['born']}")
        

        # Add ranking information for future matches only
        if is_future_match:
            if player1_info.get('num_ranking_titles') and player1_info['num_ranking_titles'] > 0:
                description_parts.append(f"Ranking Titles: {player1_info['num_ranking_titles']}")
            player1_ranking = query_player_ranking(match.Player1ID)
            if player1_ranking:
                description_parts.append(f"World Ranking: {player1_ranking['position']}")

    description_parts.append("")  # Empty line for separation

    if player2_info:
        description_parts.append(f"Player 2: {player2_name}")
        if player2_info.get('nationality'):
            description_parts.append(f"Nationality: {player2_info['nationality']}")
        if player2_info.get('born'):
            description_parts.append(f"Born: {player2_info['born']}")
        
        # Add ranking information for future matches only
        if is_future_match:
            if player2_info.get('num_ranking_titles') and player2_info['num_ranking_titles'] > 0:
                description_parts.append(f"Ranking Titles: {player2_info['num_ranking_titles']}")
            player2_ranking = query_player_ranking(match.Player2ID)
            if player2_ranking:
                description_parts.append(f"World Ranking: {player2_ranking['position']}")

    description_parts.append("")  # Empty line for separation

    # Add event details
    if event_info:
        description_parts.append(f"Event: {event_name}")
        if event_info.get('season'):
            description_parts.append(f"Season: {event_info['season']}")
        if event_info.get('venue'):
            description_parts.append(f"Venue: {event_info['venue']}")
        if event_info.get('city') and event_info.get('country'):
            description_parts.append(f"Location: {event_info['city']}, {event_info['country']}")
        elif event_info.get('city'):
            description_parts.append(f"City: {event_info['city']}")
        elif event_info.get('country'):
            description_parts.append(f"Country: {event_info['country']}")

    description_parts.append("")  # Empty line for separation
    duration_hours=3  # Default match duration in hours
    # Add round details
    if round_info:
        description_parts.append(f"Round: {round_name}")
        if round_info.get('note'):
            description_parts.append(f"Round Note: {round_info['note']}")
        if round_info.get('actual_money') and round_info['currency']:
            description_parts.append(f"Prize Money: {round_info['actual_money']} {round_info['currency']}")
        if round_info.get('distance'):
            description_parts.append(f"Match Distance: {round_info['distance']} frames")
            # Estimate match duration based on distance (assuming average 30 minutes per frame)
            duration_hours = round_info['distance'] * 0.5
            
    # Add estimated time note if applicable
    if match.Estimated:
        description_parts.append("TIME IS ESTIMATED")

    # Add URLs and notes
    if match.DetailsUrl:
        description_parts.append(f"Details: {match.DetailsUrl}")

    if match.Note:
        description_parts.append(f"Note: {match.Note}")

    if match.ExtendedNote:
        description_parts.append(f"Extended Note: {match.ExtendedNote}")

    # Add match status info
    status_info = []
    if match.WinnerID > 0:
        winner_name = player1_name if match.WinnerID == match.Player1ID else player2_name
        status_info.append(f"Winner: {winner_name}")
    elif match.Unfinished:
        status_info.append("Match Unfinished")

    if match.Walkover1 or match.Walkover2:
        walkover_name = player1_name if match.Walkover1 else player2_name
        status_info.append(f"Walkover: {walkover_name}")

    if status_info:
        description_parts.append("Status: " + ", ".join(status_info))

    # Add live URL if available
    if match.LiveUrl:
        description_parts.append(f"Live: {match.LiveUrl}")
    description_parts.append("Data source: snooker.org")
    event.add('description', '\n'.join(description_parts))

    # Add unique identifier
    event.add('uid', f"snooker-match-{match.ID}@snooker-calendar")

    # Set location if table number is available
    if match.TableNo > 0:
        event.add('location', f"Table {match.TableNo}")

        # Determine start and end times
    if match.StartDate and match.EndDate:
        # Use actual start and end dates if available
        start_time = datetime.fromisoformat(match.StartDate.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(match.EndDate.replace('Z', '+00:00'))
    else:
        # Use scheduled date and assume 3 hours duration
        scheduled_time = datetime.fromisoformat(match.ScheduledDate.replace('Z', '+00:00'))
        start_time = scheduled_time
        end_time = scheduled_time + timedelta(hours=duration_hours)

    # Ensure timezone awareness
    if start_time.tzinfo is None:
        start_time = pytz.utc.localize(start_time)
    if end_time.tzinfo is None:
        end_time = pytz.utc.localize(end_time)

    # Set event times
    event.add('dtstart', start_time)
    event.add('dtend', end_time)
    
    return event


def generate_player_calendar(player_id, year, headers=None, max_retries=3, timeout=15):
    """
    Generate ICS calendar file for a player's matches in a given year

    Args:
        player_id (int): Player ID
        year (int): Year to fetch matches for
        headers (dict): Optional headers for API requests
        max_retries (int): Maximum number of retry attempts
        timeout (int): HTTP request timeout in seconds (default: 15)

    Returns:
        str: ICS calendar content as string
    """
    # Initialize API client with timeout
    if headers is None:
        headers = {'X-Requested-By': api_config['x_requested_by']}
    
    # Create a requests session with timeout
    session = requests.Session()
    retry_strategy = Retry(
        total=0,  # No automatic retries at requests level (we handle it below)
        backoff_factor=0,
        status_forcelist=[],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Note: SnookerOrgApi doesn't expose timeout, so we'll handle it in retry logic
    client = SnookerOrgApi(headers=headers)

    # Fetch matches with retry logic and timeout protection
    matches = None
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Use timeout to prevent infinite waiting
            # This is implemented at the requests layer
            matches = client.player_matches(player_id, year)
            break  # Success, exit retry loop
        except requests.Timeout:
            last_error = "Timeout"
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # Exponential backoff: 2s, 4s, 8s
                print(f"  Attempt {attempt + 1}/{max_retries} failed: Timeout. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  All {max_retries} attempts failed (timeouts). Skipping player.")
                return None
        except requests.exceptions.JSONDecodeError:
            last_error = "Invalid JSON response"
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                print(f"  Attempt {attempt + 1}/{max_retries} failed: Invalid response. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  All {max_retries} attempts failed (invalid responses). Skipping player.")
                return None
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # Exponential backoff: 2s, 4s, 8s
                print(f"  Attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  All {max_retries} attempts failed. Skipping player. Last error: {type(e).__name__}")
                return None  # Return None instead of raising exception
    
    if not matches:
        return None

    print(f"Found {len(matches)} matches")
    player_info = query_player_info(player_id)
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//Snooker Calendar Generator//snooker-calendar//')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    if player_info:
        if player_info.get('surname_first', False):
            player_name = f"{player_info['lastname']}, {player_info['firstname']}"
        else:
            player_name = f"{player_info['firstname']} {player_info['lastname']}"
        cal.add('name', f'Snooker Matches - {player_name} ({year})')
        cal.add('x-wr-calname', f'Snooker Matches - {player_name} ({year})')
        cal.add('description', f'Snooker matches for {player_name}, Data source: snooker.org, last updated {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}')

    # Add events
    for match in matches:
        try:
            event = create_match_event(match, player_id)
            cal.add_component(event)
        except Exception as e:
            print(f"  Warning - Error processing match {match.ID}: {type(e).__name__}")
            continue  # Skip this match and continue with others

    # Return bytes to preserve CRLF line endings and proper RFC5545 folding
    return cal.to_ical()


def main():
    """
    Main function to handle command line arguments and generate calendar
    """
    if len(sys.argv) < 3:
        print("Usage: python player_matches_to_ics.py <player_id> <year> [output_file.ics]")
        print("Example: python player_matches_to_ics.py 5 2025 ronnie_osullivan_2025.ics")
        sys.exit(1)

    player_id = int(sys.argv[1])
    year = int(sys.argv[2])
    output_file = sys.argv[3] if len(sys.argv) > 3 else f"player_{player_id}_{year}.ics"

    try:
        # Generate calendar (bytes)
        ics_bytes = generate_player_calendar(player_id, year)

        if ics_bytes is None:
            print("No matches found, exiting.")
            sys.exit(1)

        # Write bytes to file to preserve CRLF and folding
        with open(output_file, 'wb') as f:
            f.write(ics_bytes)

        print(f"Successfully created calendar file: {output_file}")
        # Count VEVENT occurrences in bytes
        print(f"Calendar contains events for {ics_bytes.count(b'BEGIN:VEVENT')} matches")

    except Exception as e:
        print(f"Error generating calendar: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()