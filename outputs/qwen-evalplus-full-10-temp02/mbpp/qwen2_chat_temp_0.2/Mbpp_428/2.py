def shell_sort(arr):
    # Start with a gap of 1
    gap = 1
    # Continue until the gap is no longer greater than the length of the array
    while gap < len(arr):
        # Perform a shell sort pass
        for i in range(gap, len(arr)):
            # Store the current element
            temp = arr[i]
            # Find the correct position for the current element
            j = i
            while j >= gap and arr[j - gap] > temp:
                arr[j] = arr[j - gap]
                j -= gap
            # Place the current element at its correct position
            arr[j] = temp
        # Increase the gap for the next pass
        gap *= 2
    return arr