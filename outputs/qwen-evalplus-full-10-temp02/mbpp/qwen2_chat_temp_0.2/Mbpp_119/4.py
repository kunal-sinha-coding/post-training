def search(arr):
    # Initialize the result to the first element of the array
    result = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Check if the current element is not equal to the result
        if arr[i] != result:
            # If not, update the result
            result = arr[i]
    # Return the result
    return result