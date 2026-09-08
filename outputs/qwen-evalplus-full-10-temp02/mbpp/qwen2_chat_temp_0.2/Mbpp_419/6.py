def round_and_sum(numbers):
    """
    Round every number of the given list of numbers and print the total sum multiplied by the length of the list.
    
    :param numbers: List of numbers to be processed.
    :return: The total sum multiplied by the length of the list.
    """
    total_sum = 0
    for number in numbers:
        rounded_number = round(number)
        total_sum += rounded_number
    return total_sum * len(numbers)
