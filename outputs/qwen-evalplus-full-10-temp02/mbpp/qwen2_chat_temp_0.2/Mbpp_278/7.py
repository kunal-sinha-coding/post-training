def count_first_elements(tup):
    # Initialize a counter for the number of elements before the tuple element
    count = 0
    # Iterate through the tuple
    for i in range(len(tup)):
        # Check if the current element is the first element in the tuple
        if i == 0:
            count += 1
    # Return the count of elements before the tuple element
    return count