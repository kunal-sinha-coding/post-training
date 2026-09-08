def count_first_elements(tup):
    """
    This function takes a tuple as input and returns the count of elements that occur before the tuple element.
    
    Parameters:
    tup (tuple): The input tuple.
    
    Returns:
    int: The count of elements before the tuple element.
    """
    # Initialize a counter to zero
    count = 0
    # Iterate through the tuple
    for i in range(len(tup)):
        # Check if the current element is equal to the tuple element
        if tup[i] == tup[i-1]:
            count += 1
    return count
