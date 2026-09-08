# Define a function to count the number of integer elements in a list
def count_integer(lst):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is an integer
        if isinstance(element, int):
            # Increment the counter if it is an integer
            count += 1
    # Return the total count of integer elements
    return count