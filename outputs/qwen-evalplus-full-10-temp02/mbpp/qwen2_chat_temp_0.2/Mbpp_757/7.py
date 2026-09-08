def count_reverse_pairs(strings):
    """
    This function counts the pairs of reverse strings in the given list.
    
    Args:
    strings (list): A list of strings.
    
    Returns:
    int: The count of pairs of reverse strings.
    """
    count = 0
    for i in range(len(strings)):
        for j in range(i + 1, len(strings)):
            if strings[i] == strings[j][::-1]:
                count += 1
    return count