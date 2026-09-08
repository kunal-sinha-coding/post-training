def count_first_elements(test_tuple):
    """
    This function takes a tuple as input and returns the count of elements that precede the tuple element.
    
    Parameters:
    test_tuple (tuple): The input tuple.
    
    Returns:
    int: The count of elements before the tuple element.
    """
    # Initialize a counter to zero
    count = 0
    # Iterate through the tuple
    for element in test_tuple:
        # Check if the current element is the tuple element
        if element == test_tuple:
            # Increment the counter
            count += 1
    # Return the count of elements before the tuple element
    return count
