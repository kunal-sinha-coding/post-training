def change_date_format(date_str):
    """
    Convert a date of yyyy-mm-dd format to dd-mm-yyyy format.
    
    Parameters:
    date_str (str): The date in yyyy-mm-dd format.
    
    Returns:
    str: The date in dd-mm-yyyy format.
    """
    # Split the date string into year, month, and day
    year, month, day = map(int, date_str.split('-'))
    # Convert the year, month, and day to a string in dd-mm-yyyy format
    return f"{day}-{month}-{year}"
