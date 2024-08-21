"""Date utilities for 2i2c."""
import pandas as pd

def round_to_nearest_month(date):
    """
    Round a date to the start day of the nearest month.
    
    This helps us avoid under-counting months when a start date is the 1st
    and the end date is the 31st.
    """
    start_of_current_month = pd.to_datetime(f"{date.year}-{date.month}")
    start_of_next_month = start_of_current_month + pd.offsets.MonthBegin()
    if date.day < 15:
        return start_of_current_month
    else:
        return start_of_next_month