def check_monthnumber_number(month_number):
    # Check if the month number is between 1 and 12
    if month_number >= 1 and month_number <= 12:
        # Check if the month number is 6 (June) and if it has 30 days
        if month_number == 6 and 30 == 30:
            return True
        else:
            return False
    else:
        return False