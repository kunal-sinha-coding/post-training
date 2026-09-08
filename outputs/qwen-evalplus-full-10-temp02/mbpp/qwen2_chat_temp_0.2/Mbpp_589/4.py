def perfect_squares(start, end):
    """
    Find perfect squares between two given numbers.
    
    Parameters:
    start (int): The starting number.
    end (int): The ending number.
    
    Returns:
    list: A list of perfect squares between start and end.
    """
    perfect_squares = []
    for num in range(start, end + 1):
        if num ** 0.5 == int(num ** 0.5):
            perfect_squares.append(num)
    return perfect_squares
