def count_integer(lst):
    """
    This function takes a list as input and returns the count of integer elements in the list.
    
    Parameters:
    lst (list): The input list containing elements of various data types.
    
    Returns:
    int: The count of integer elements in the list.
    """
    # Initialize a counter for integer elements
    integer_count = 0
    
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is an integer
        if isinstance(element, int):
            # Increment the counter if it is an integer
            integer_count += 1
    
    # Return the total count of integer elements
    return integer_count