def sample_nam(names):
    # Initialize a counter for the sum of names
    total_length = 0
    
    # Iterate through each name in the list
    for name in names:
        # Check if the name starts with a lowercase letter
        if name[0].islower():
            # Add the length of the name to the total length
            total_length += len(name)
    
    # Return the total length of names that start with a lowercase letter
    return total_length