def check_monthnumb_number(month):
    # Define the number of days in each month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Check if the given month number is in the list of days in the month
    if month in days_in_month:
        return True
    else:
        return False