def sample_nam(names):
    """
    This function takes a list of names and returns the sum of the lengths of the names that start with a lowercase letter.
    
    Parameters:
    names (list): A list of names.
    
    Returns:
    int: The sum of the lengths of the names that start with a lowercase letter.
    """
    # Initialize the sum to 0
    total_length = 0
    
    # Iterate over each name in the list
    for name in names:
        # Check if the name starts with a lowercase letter
        if name[0].islower():
            # Add the length of the name to the total length
            total_length += len(name)
    
    # Return the total length
    return total_length