def count_first_elements(test_tuple):
    # Initialize a counter to keep track of the number of elements before the tuple element
    count = 0
    # Iterate through the tuple starting from the second element
    for element in test_tuple[1:]:
        # Increment the counter for each element except the first one
        count += 1
    # Return the total count of elements before the tuple element
    return count