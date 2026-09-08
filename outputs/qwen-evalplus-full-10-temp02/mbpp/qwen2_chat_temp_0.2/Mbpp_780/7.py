from itertools import combinations

def find_combinations(tup_list):
    """
    This function takes a tuple list as input and returns a list of tuples that sum up to a given number.
    
    Parameters:
    tup_list (tuple): A list of tuples to find combinations from.
    
    Returns:
    list: A list of tuples that sum up to the given number.
    """
    # Initialize an empty list to store the combinations
    result = []
    # Iterate over each tuple in the input list
    for tup in tup_list:
        # Calculate the sum of the current tuple
        current_sum = sum(tup)
        # Check if the current sum is equal to the target number
        if current_sum == target:
            # If it is, add the tuple to the result list
            result.append(tup)
    return result
