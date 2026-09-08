def check_monthnumb_number(month):
    # Define the number of days in each month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check if the given month number is within the valid range
    if month < 1 or month > 12:
        return False
    
    # Return True if the month has 31 days, otherwise False
    return days_in_month[month - 1] == 31