def find_first_occurrence(arr, x):
    # Initialize the index to -1, as x is not found in the array
    index = -1
    # Iterate through the array starting from the first element
    for i in range(len(arr)):
        # Check if the current element matches x
        if arr[i] == x:
            # Update the index if the current element is found
            index = i
    # Return the index of the first occurrence of x, or -1 if x is not found
    return index