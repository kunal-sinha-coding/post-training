def find_first_occurrence(arr, x):
    # Initialize the index to -1, as x is not found in the array
    index = -1
    # Iterate through the array starting from the first element
    for i in range(len(arr)):
        # Check if the current element is equal to x
        if arr[i] == x:
            # If it is, update the index to the current index
            index = i
            # Break out of the loop as we found the first occurrence
            break
    # Return the index of the first occurrence of x
    return index