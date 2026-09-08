def check_monthnumber_number(month_number):
    # Define the number of days in each month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check if the given month number is within the valid range
    if month_number < 1 or month_number > 12:
        return False
    
    # Return True if the month contains 30 days
    return days_in_month[month_number - 1] == 30