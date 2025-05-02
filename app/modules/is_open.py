import pandas as pd
from datetime import datetime, time

def is_open_at_time(row: pd.Series, check_time: datetime) -> bool:
    check_day = check_time.weekday()  # Monday = 0
    check_t = check_time.time()

    for i in range(7):
        try:
            open_day = row.get(f"regularOpeningHours.periods[{i}].open.day")
            close_day = row.get(f"regularOpeningHours.periods[{i}].close.day")
            open_hour = row.get(f"regularOpeningHours.periods[{i}].open.hour")
            open_minute = row.get(f"regularOpeningHours.periods[{i}].open.minute")
            close_hour = row.get(f"regularOpeningHours.periods[{i}].close.hour")
            close_minute = row.get(f"regularOpeningHours.periods[{i}].close.minute")

            # Skip if any required value is missing
            if any(pd.isnull(x) for x in [open_day, close_day, open_hour, open_minute, close_hour, close_minute]):
                continue

            open_t = time(int(open_hour), int(open_minute))
            close_t = time(int(close_hour), int(close_minute))

            # Case 1: Same day open/close
            if open_day == close_day == check_day:
                if open_t <= check_t <= close_t:
                    return True

            # Case 2: Overnight open (e.g. 22:00 to 02:00 next day)
            elif open_day == check_day and open_day != close_day:
                if check_t >= open_t:
                    return True
            elif close_day == check_day and open_day != close_day:
                if check_t <= close_t:
                    return True

        except Exception as e:
            # Optional: Add logging here
            print(f"Skipping row due to error: {e}")
            continue

    return False


# def is_open_at_time(row: pd.Series, check_time: datetime) -> bool:
#     """
#     Checks if a restaurant is open at the given datetime.
    
#     Args:
#         row: A single row from the DataFrame containing structured open/close fields
#         check_time: A datetime object to check (e.g., Monday at 12:00)
        
#     Returns:
#         True if open, False otherwise
#     """
#     check_day = check_time.weekday()  # Monday = 0
#     check_t = check_time.time()

#     for i in range(7):
#         open_day = row.get(f"regularOpeningHours.periods[{i}].open.day")
#         close_day = row.get(f"regularOpeningHours.periods[{i}].close.day")
#         open_hour = row.get(f"regularOpeningHours.periods[{i}].open.hour")
#         open_minute = row.get(f"regularOpeningHours.periods[{i}].open.minute")
#         close_hour = row.get(f"regularOpeningHours.periods[{i}].close.hour")
#         close_minute = row.get(f"regularOpeningHours.periods[{i}].close.minute")

#         # Skip if any field is missing
#         if pd.isnull(open_day) or pd.isnull(close_day):
#             continue

#         open_t = time(int(open_hour), int(open_minute))
#         close_t = time(int(close_hour), int(close_minute))

#         # Case 1: Open and close on the same day
#         if open_day == close_day == check_day:
#             if open_t <= check_t <= close_t:
#                 return True

#         # Case 2: Overnight opening (e.g. open 22:00, close 02:00 next day)
#         elif open_day == check_day and open_day != close_day:
#             if check_t >= open_t:
#                 return True
#         elif close_day == check_day and open_day != close_day:
#             if check_t <= close_t:
#                 return True

#     return False
