def is_majority(arr, n, x):
    # Initialize a counter for the element
    count = 0
    # Iterate through the array
    for i in range(n):
        # Check if the current element is equal to x
        if arr[i] == x:
            count += 1
    # Check if the count is greater than n/2
    if count > n // 2:
        return True
    else:
        return False