def round_and_sum(numbers):
    """
    Round every number in the given list of numbers and print the total sum multiplied by the length of the list.
    
    :param numbers: List of numbers to be rounded and summed.
    :return: Total sum of rounded numbers multiplied by the length of the list.
    """
    total_sum = sum(round(num) for num in numbers)
    length = len(numbers)
    return total_sum * length
