# Define a function to count the occurrences of a number in a list
def frequency(lst, num):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the list
    for i in lst:
        # Check if the current element is equal to the target number
        if i == num:
            # Increment the counter if it is
            count += 1
    # Return the total count of occurrences
    return count