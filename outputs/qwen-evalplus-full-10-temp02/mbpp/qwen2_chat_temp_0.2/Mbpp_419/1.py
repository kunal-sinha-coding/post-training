def round_and_sum(numbers):
    """
    Round every number in the given list of numbers and print the total sum multiplied by the length of the list.
    
    Parameters:
    numbers (list): A list of numbers to be rounded and summed.
    
    Returns:
    int: The total sum multiplied by the length of the list.
    """
    total_sum = 0
    for number in numbers:
        rounded_number = round(number)
        total_sum += rounded_number
    return total_sum * len(numbers)
