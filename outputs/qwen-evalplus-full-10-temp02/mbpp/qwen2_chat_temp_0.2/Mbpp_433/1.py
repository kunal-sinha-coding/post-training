def check_greater(arr, n):
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Check if the current element is greater than the previous element
        if arr[i] > arr[i - 1]:
            return True
    # If no such element is found, return False
    return False