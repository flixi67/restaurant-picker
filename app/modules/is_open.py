import re
from datetime import time

def is_open(day_descriptions, meeting_day, meeting_hour, meeting_minute):
    """
    Super simple standalone function that only uses primitive types.
    
    Args:
        day_descriptions: List of strings like ['Monday: 9:00 AM - 5:00 PM', ...] 
        meeting_day: Integer (0=Monday, 6=Sunday)
        meeting_hour: Hour in 24-hour format (0-23)
        meeting_minute: Minute (0-59)
        
    Returns:
        Boolean indicating if restaurant is open
    """
    # Convert day number to name
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[meeting_day]
    
    # Find the description for this day
    day_desc = None
    for desc in day_descriptions:
        if desc.startswith(day_name + ":"):
            day_desc = desc
            break
    
    # Not found or closed
    if day_desc is None or "Closed" in day_desc:
        return False
    
    # Create time object for current time
    current_time = time(meeting_hour, meeting_minute)
    
    # Extract time ranges using regex
    time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*([APap][Mm])\s*[–-]\s*(\d{1,2})(?::(\d{2}))?\s*([APap][Mm])'
    time_ranges = re.findall(time_pattern, day_desc)
    
    # No time ranges found
    if not time_ranges:
        # Try with comma-separated slots
        for slot in day_desc.split(','):
            slot_times = re.findall(time_pattern, slot)
            if slot_times and is_in_time_range(slot_times[0], current_time):
                return True
        return False
    
    # Check each time range
    for time_range in time_ranges:
        if is_in_time_range(time_range, current_time):
            return True
    
    return False

def is_in_time_range(time_range, current_time):
    """
    Check if current_time is in the given time range.
    """
    try:
        open_hour = int(time_range[0])
        open_min = int(time_range[1]) if time_range[1] else 0
        open_ampm = time_range[2].upper()
        
        close_hour = int(time_range[3])
        close_min = int(time_range[4]) if time_range[4] else 0
        close_ampm = time_range[5].upper()
        
        # Convert to 24-hour format
        if open_hour == 12:
            open_hour = 0 if open_ampm == 'AM' else 12
        elif open_ampm == 'PM' and open_hour < 12:
            open_hour += 12
            
        if close_hour == 12:
            close_hour = 0 if close_ampm == 'AM' else 12
        elif close_ampm == 'PM' and close_hour < 12:
            close_hour += 12
        
        # Create time objects
        open_time = time(open_hour, open_min)
        close_time = time(close_hour, close_min)
        
        # Check if current time is in range
        if open_hour > close_hour:  # Overnight
            return current_time >= open_time or current_time <= close_time
        else:  # Same day
            return open_time <= current_time <= close_time
            
    except (ValueError, IndexError):
        return False