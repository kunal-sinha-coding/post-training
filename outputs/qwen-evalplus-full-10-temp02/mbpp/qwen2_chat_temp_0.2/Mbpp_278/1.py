def count_first_elements(test_tuple):
    """
    This function takes a tuple as input and returns the count of elements that occur before the tuple element.
    
    Parameters:
    test_tuple (tuple): The input tuple.
    
    Returns:
    int: The count of elements before the tuple element.
    """
    # Initialize a counter for the elements before the tuple element
    count = 0
    # Iterate through the tuple starting from the second element
    for i in range(1, len(test_tuple)):
        # If the current element is not the tuple element, increment the counter
        if test_tuple[i] != test_tuple[0]:
            count += 1
    return count
