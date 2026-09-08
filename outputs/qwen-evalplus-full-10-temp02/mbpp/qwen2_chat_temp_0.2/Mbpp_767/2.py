def get_pairs_count(numbers, sum):
    """
    Count the number of pairs whose sum is equal to 'sum'. The function gets as input a list of numbers and the sum,
    and returns the count of such pairs.
    
    :param numbers: List of integers
    :param sum: Integer representing the target sum
    :return: Integer count of pairs whose sum is equal to 'sum'
    """
    count = 0
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] + numbers[j] == sum:
                count += 1
    return count
