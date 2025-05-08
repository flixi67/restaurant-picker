import pandas as pd
import re
from datetime import datetime, time

def is_open_at_time(row: pd.Series, check_time: datetime) -> bool:
    """
    Determines if a restaurant is open by chhecking against the data fields in API.
    
    Args:
        row: DataFrame row containing restaurant data
        check_time: Datetime object representing when the meeting will occur
        
    Returns:
        Boolean indicating if the restaurant is likely open
    """
    # Get day of week name and hour
    python_weekday = check_time.weekday()  # 0=Monday, 6=Sunday
    google_weekday = (python_weekday + 1) % 7  # 0=Sunday, 1=Monday
    
    check_hour = check_time.hour
    check_minute = check_time.minute
    
    # First, some safe fallbacks:
    # Standard business hours: assume open 8am-10pm for most restaurants
    standard_hours = 8 <= check_hour <= 22
    
    # Look for periods in the data (one by one to avoid array truth issues)
    for i in range(7):  # Check each possible period
        # Column names for this period
        open_day_col = f"regularOpeningHours.periods[{i}].open.day"
        
        # Only process if this period exists
        if open_day_col in row.index:
            try:
                # Get values, ensuring scalar extraction with .item() if needed
                get_value = lambda col: row[col].item() if hasattr(row[col], 'item') else row[col]
                
                open_day = int(float(get_value(open_day_col)))
                close_day_col = f"regularOpeningHours.periods[{i}].close.day"
                close_day = int(float(get_value(close_day_col)))
                
                open_hour_col = f"regularOpeningHours.periods[{i}].open.hour"
                open_hour = int(float(get_value(open_hour_col)))
                
                open_min_col = f"regularOpeningHours.periods[{i}].open.minute"
                open_min = int(float(get_value(open_min_col)))
                
                close_hour_col = f"regularOpeningHours.periods[{i}].close.hour"
                close_hour = int(float(get_value(close_hour_col)))
                
                close_min_col = f"regularOpeningHours.periods[{i}].close.minute"
                close_min = int(float(get_value(close_min_col)))
                
                # Create time objects
                open_time = time(open_hour, open_min)
                close_time = time(close_hour, close_min)
                current_time = time(check_hour, check_minute)
                
                # Check if day matches and time is within range
                if open_day == close_day == google_weekday:
                    # Same day opening (e.g., 9am-5pm)
                    if open_time <= current_time <= close_time:
                        return True
                
                elif open_day == google_weekday:
                    # Start of overnight hours (e.g., open Friday 5pm)
                    if current_time >= open_time:
                        return True
                        
                elif close_day == google_weekday:
                    # End of overnight hours (e.g., close Saturday 2am)
                    if current_time <= close_time:
                        return True
                
            except (ValueError, TypeError, AttributeError) as e:
                # If any error occurs with this period, just skip it
                continue
    
    # If we got here, we didn't find a matching open period
    # Return standard business hours as fallback
    return False