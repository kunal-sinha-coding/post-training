def shell_sort(arr):
    # Start with the length of the array
    n = len(arr)
    # Start with the largest possible gap
    gap = n // 2
    
    # Continue until the gap is 0
    while gap > 0:
        # Perform a gapped insertion sort
        for i in range(gap, n):
            # Store the current element
            temp = arr[i]
            # Find the correct position for the current element
            j = i
            while j >= gap and arr[j - gap] > temp:
                arr[j] = arr[j - gap]
                j -= gap
            # Place the current element at its correct position
            arr[j] = temp
        # Reduce the gap
        gap = gap // 2
    return arr