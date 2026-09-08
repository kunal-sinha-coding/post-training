def find_first_occurrence(arr, x):
    # Initialize the index to -1, which means the number is not found
    index = -1
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the current element is equal to the target number
        if arr[i] == x:
            # Update the index if the current element is found
            index = i
    # Return the index of the first occurrence of the number
    return index