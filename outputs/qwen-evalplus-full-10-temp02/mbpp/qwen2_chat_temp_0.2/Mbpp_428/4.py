def shell_sort(arr):
    # Start with the length of the array
    n = len(arr)
    # Start with a gap of n/2
    gap = n // 2
    
    # Continue until the gap is 0
    while gap > 0:
        # Perform a selection sort on the array with the current gap
        for i in range(gap, n):
            # Assume the current element is the smallest
            min_index = i
            # Compare the current element with the elements in the gap
            for j in range(i + gap, n):
                if arr[j] < arr[min_index]:
                    min_index = j
            # Swap the found smallest element with the current element
            arr[i], arr[min_index] = arr[min_index], arr[i]
        # Reduce the gap by half
        gap = gap // 2
    
    return arr