def count_first_elements(tup):
    # Initialize a counter to zero
    count = 0
    # Iterate through the tuple
    for i in range(len(tup)):
        # Check if the current element is a tuple
        if isinstance(tup[i], tuple):
            # Increment the counter for each tuple found
            count += 1
    # Return the count of elements before the tuple element
    return count