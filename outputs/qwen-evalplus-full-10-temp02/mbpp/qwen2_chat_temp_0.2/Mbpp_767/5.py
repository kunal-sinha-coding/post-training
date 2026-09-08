def get_pairs_count(numbers, sum):
    """
    Counts the number of pairs whose sum is equal to the given sum.
    
    Args:
    numbers (list): A list of integers.
    sum (int): The target sum to find pairs for.
    
    Returns:
    int: The count of pairs whose sum is equal to the given sum.
    """
    count = 0
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] + numbers[j] == sum:
                count += 1
    return count
