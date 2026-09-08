def shell_sort(arr):
    # Start with a gap of 1
    gap = 1
    # Continue until the gap is no longer greater than the length of the array
    while gap < len(arr):
        # Perform a insertion sort on the array with the current gap
        for i in range(gap, len(arr)):
            key = arr[i]
            j = i - gap
            # Move elements of arr[0..i-gap] that are greater than key to one position ahead
            while j >= 0 and key < arr[j]:
                arr[j + gap] = arr[j]
                j -= gap
            # Place the key at its correct position
            arr[j + gap] = key
        # Decrease the gap for the next pass
        gap *= 2
    return arr