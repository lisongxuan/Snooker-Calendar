#!/usr/bin/env python3
"""
Script to convert snooker player matches to ICS calendar format
"""
import configparser
import sys
from datetime import datetime, timedelta
from snooker.api import SnookerOrgApi
from icalendar import Calendar, Event, vText
import pytz
from query_data import query_player_info, query_event_info, query_round_info, query_player_ranking
def load_config(filename='config.txt'):
    config = configparser.ConfigParser()
    config.read(filename)

    # Load database configuration
    db_config = {key: value for key, value in config['database'].items()}

    # Load API configuration
    api_config = {key: value for key, value in config['api'].items()}

    return db_config, api_config
db_config, api_config = load_config()

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

    # Determine start and end times
    if match.StartDate and match.EndDate:
        # Use actual start and end dates if available
        start_time = datetime.fromisoformat(match.StartDate.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(match.EndDate.replace('Z', '+00:00'))
    else:
        # Use scheduled date and assume 3 hours duration
        scheduled_time = datetime.fromisoformat(match.ScheduledDate.replace('Z', '+00:00'))
        start_time = scheduled_time
        end_time = scheduled_time + timedelta(hours=3)

    # Ensure timezone awareness
    if start_time.tzinfo is None:
        start_time = pytz.utc.localize(start_time)
    if end_time.tzinfo is None:
        end_time = pytz.utc.localize(end_time)

    # Set event times
    event.add('dtstart', start_time)
    event.add('dtend', end_time)

    # Query additional information
    player1_info = query_player_info(match.Player1ID)
    player2_info = query_player_info(match.Player2ID)
    event_info = query_event_info(match.EventID)
    round_info = query_round_info(match.EventID, match.Round)

    # Check if this is a future match
    is_future_match = match.Unfinished

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
        if player1_info.get('num_ranking_titles') and player1_info['num_ranking_titles'] > 0:
            description_parts.append(f"Ranking Titles: {player1_info['num_ranking_titles']}")

        # Add ranking information for future matches only
        if is_future_match:
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
        if player2_info.get('num_ranking_titles') and player2_info['num_ranking_titles'] > 0:
            description_parts.append(f"Ranking Titles: {player2_info['num_ranking_titles']}")

        # Add ranking information for future matches only
        if is_future_match:
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
        if event_info.get('type'):
            description_parts.append(f"Type: {event_info['type']}")

    description_parts.append("")  # Empty line for separation

    # Add round details
    if round_info:
        description_parts.append(f"Round: {round_name}")
        if round_info.get('note'):
            description_parts.append(f"Round Note: {round_info['note']}")
        if round_info.get('value_type'):
            description_parts.append(f"Value Type: {round_info['value_type']}")
        if round_info.get('rank'):
            description_parts.append(f"Rank: {round_info['rank']}")

    # Add estimated time note if applicable
    if match.Estimated:
        description_parts.append("⚠️ TIME IS ESTIMATED")

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

    # Add IDs for reference
    description_parts.append("")
    description_parts.append(f"Event ID: {match.EventID} | Round: {match.Round} | Player1 ID: {match.Player1ID} | Player2 ID: {match.Player2ID}")

    event.add('description', '\n'.join(description_parts))

    # Add unique identifier
    event.add('uid', f"snooker-match-{match.ID}@snooker-calendar")

    # Set location if table number is available
    if match.TableNo > 0:
        event.add('location', f"Table {match.TableNo}")

    return event


def generate_player_calendar(player_id, year, headers=None):
    """
    Generate ICS calendar file for a player's matches in a given year

    Args:
        player_id (int): Player ID
        year (int): Year to fetch matches for
        headers (dict): Optional headers for API requests

    Returns:
        str: ICS calendar content as string
    """
    # Initialize API client
    if headers is None:
        headers = {'X-Requested-By': api_config['x_requested_by']}
    client = SnookerOrgApi(headers=headers)

    # Fetch matches
    print(f"Fetching matches for player {player_id} in year {year}...")
    matches = client.player_matches(player_id, year)

    if not matches:
        print(f"No matches found for player {player_id} in {year}")
        return None

    print(f"Found {len(matches)} matches")

    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//Snooker Calendar Generator//snooker-calendar//')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('name', f'Snooker Matches - Player {player_id} ({year})')
    cal.add('x-wr-calname', f'Snooker Matches - Player {player_id} ({year})')
    cal.add('description', f'Snooker matches for player ID {player_id} in {year}')

    # Add events
    for match in matches:
        try:
            event = create_match_event(match, player_id)
            cal.add_component(event)
            print(f"Added match: EventID={match.EventID}, Round={match.Round}")
        except Exception as e:
            print(f"Error processing match {match.ID}: {e}")
            continue

    return cal.to_ical().decode('utf-8')


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
        # Generate calendar
        ics_content = generate_player_calendar(player_id, year)

        if ics_content is None:
            print("No matches found, exiting.")
            sys.exit(1)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ics_content)

        print(f"Successfully created calendar file: {output_file}")
        print(f"Calendar contains events for {ics_content.count('BEGIN:VEVENT')} matches")

    except Exception as e:
        print(f"Error generating calendar: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()