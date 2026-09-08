def round_and_sum(numbers):
    """
    Rounds every number in the given list of numbers and prints the total sum multiplied by the length of the list.
    
    :param numbers: List of numbers to be processed.
    :return: The total sum multiplied by the length of the list.
    """
    total_sum = sum(round(num) for num in numbers)
    length = len(numbers)
    print(total_sum * length)