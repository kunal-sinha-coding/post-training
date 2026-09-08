def find_even_pair(numbers):
    """
    Counts the number of pairs of integers in the list that xor to an even number.
    
    :param numbers: List of integers
    :return: Count of even pairs
    """
    even_count = 0
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if (numbers[i] ^ numbers[j]) % 2 == 0:
                even_count += 1
    return even_count