def check_monthnumb_number(monthnumb):
    # Define the number of days in each month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check if the given month number is within the valid range (1 to 12)
    if monthnumb < 1 or monthnumb > 12:
        return False
    
    # Return True if the month number contains 31 days
    return days_in_month[monthnumb - 1] == 31
