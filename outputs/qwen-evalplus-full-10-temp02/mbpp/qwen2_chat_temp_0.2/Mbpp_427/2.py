def change_date_format(date_str):
    """
    Convert a date of yyyy-mm-dd format to dd-mm-yyyy format.
    
    Args:
    date_str (str): The date in yyyy-mm-dd format.
    
    Returns:
    str: The date in dd-mm-yyyy format.
    """
    # Split the date string into year, month, and day
    year, month, day = map(int, date_str.split('-'))
    # Convert the day to a string with leading zeros if necessary
    day_str = str(day).zfill(2)
    # Combine the year, month, and day in the desired format
    return f"{month}-{day_str}-{year}"
