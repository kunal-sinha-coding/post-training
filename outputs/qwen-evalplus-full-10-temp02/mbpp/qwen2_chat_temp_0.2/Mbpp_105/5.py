def count(lst):
    # Initialize a counter for true booleans
    true_count = 0
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is True
        if element:
            # Increment the counter if the element is True
            true_count += 1
    # Return the total count of true booleans
    return true_count