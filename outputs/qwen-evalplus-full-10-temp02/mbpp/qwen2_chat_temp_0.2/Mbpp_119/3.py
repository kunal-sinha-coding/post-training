def search(arr):
    # Initialize a variable to store the result
    result = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Check if the current element is not equal to the previous one
        if arr[i] != arr[i - 1]:
            # Update the result with the current element
            result = arr[i]
    # Return the result
    return result