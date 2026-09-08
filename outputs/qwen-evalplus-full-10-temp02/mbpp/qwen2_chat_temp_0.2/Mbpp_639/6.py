def sample_nam(names):
    # Initialize a counter for the length of names that start with a lowercase letter
    count = 0
    # Iterate through each name in the list
    for name in names:
        # Check if the name starts with a lowercase letter
        if name[0].islower():
            # Increment the counter if the condition is met
            count += 1
    # Return the total count of names that start with a lowercase letter
    return count