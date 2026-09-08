def get_pairs_count(numbers, sum):
    """
    Count the number of pairs whose sum is equal to 'sum'.
    
    Args:
    numbers (list): A list of integers.
    sum (int): The target sum.
    
    Returns:
    int: The count of pairs whose sum is equal to 'sum'.
    """
    count = 0
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] + numbers[j] == sum:
                count += 1
    return count
