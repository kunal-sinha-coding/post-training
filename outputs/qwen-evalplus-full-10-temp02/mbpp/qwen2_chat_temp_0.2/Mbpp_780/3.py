from itertools import combinations

def find_combinations(tup_list):
    """
    This function takes a tuple list as input and returns a list of tuples that sum up to a given number.
    
    Parameters:
    tup_list (tuple): A list of tuples.
    
    Returns:
    list: A list of tuples that sum up to the given number.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over each tuple in the input list
    for tup in tup_list:
        # Iterate over all possible combinations of the tuple
        for combo in combinations(tup, 2):
            # Check if the sum of the two tuples equals the given number
            if sum(combo) == number:
                # Append the tuple to the result list
                result.append(combo)
    return result
