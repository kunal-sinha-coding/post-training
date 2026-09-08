def shell_sort(arr):
    # Start with the length of the array
    n = len(arr)
    # Start with the gap size
    gap = n // 2
    
    # Continue until the gap is 0
    while gap > 0:
        # Perform a shell sort pass
        for i in range(gap, n):
            # Store the current element
            temp = arr[i]
            # Move elements that are greater than the current element
            j = i
            while j >= gap and arr[j - gap] > temp:
                arr[j] = arr[j - gap]
                j -= gap
            # Place the current element at its correct position
            arr[j] = temp
        # Reduce the gap size
        gap = gap // 2
    
    return arr