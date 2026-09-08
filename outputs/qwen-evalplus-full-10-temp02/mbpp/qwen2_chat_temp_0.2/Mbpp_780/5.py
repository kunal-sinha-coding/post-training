def find_combinations(tup_list):
    """
    Find the combinations of sums with tuples in the given tuple list.
    
    Args:
    tup_list (list of tuples): A list of tuples.
    
    Returns:
    list of tuples: A list of tuples containing combinations of sums with tuples.
    """
    result = []
    for i in range(len(tup_list)):
        for j in range(i + 1, len(tup_list)):
            for k in range(j + 1, len(tup_list)):
                if tup_list[i] + tup_list[j] + tup_list[k] == 0:
                    result.append((tup_list[i], tup_list[j], tup_list[k]))
    return result
