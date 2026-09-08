def combinations_list(lst):
    """
    Find all possible combinations of the elements of a given list.
    
    Args:
    lst (list): A list of elements.
    
    Returns:
    list: A list of all possible combinations of the elements.
    """
    # Initialize an empty list to store the combinations
    result = []
    # Iterate over each element in the list
    for i in range(len(lst)):
        # Iterate over each element in the current combination
        for j in range(i + 1, len(lst)):
            # Add the current combination to the result list
            result.append(lst[i:j])
    return result
