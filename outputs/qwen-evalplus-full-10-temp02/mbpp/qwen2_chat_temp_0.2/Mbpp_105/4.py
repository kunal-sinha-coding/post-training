def count(list1):
    # Initialize a counter for true booleans
    count = 0
    # Iterate through each element in the list
    for element in list1:
        # Check if the element is True
        if element:
            # Increment the counter if the element is True
            count += 1
    # Return the total count of true booleans
    return count