def count(lst):
    """
    This function takes a list of boolean values and returns the count of true booleans.
    
    Args:
    lst (list): A list containing boolean values.
    
    Returns:
    int: The count of true booleans in the list.
    """
    # Initialize a counter for true booleans
    true_count = 0
    
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is true
        if element:
            # Increment the counter if true
            true_count += 1
    
    # Return the total count of true booleans
    return true_count