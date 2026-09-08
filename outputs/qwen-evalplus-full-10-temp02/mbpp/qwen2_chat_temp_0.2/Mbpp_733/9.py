def find_first_occurrence(arr, x):
    # Initialize the index to -1, as x is not found in the array
    index = -1
    # Iterate through the array to find the first occurrence of x
    for i in range(len(arr)):
        # If the current element matches x, update the index
        if arr[i] == x:
            index = i
            break
    # Return the index of the first occurrence of x
    return index