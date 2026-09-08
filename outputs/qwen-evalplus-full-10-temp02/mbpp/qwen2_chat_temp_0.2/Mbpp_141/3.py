def pancake_sort(arr):
    n = len(arr)
    for i in range(n-1, 0, -1):
        # Find the index of the maximum element in the unsorted part of the array
        max_index = i
        for j in range(i+1, n):
            if arr[j] > arr[max_index]:
                max_index = j
        # Swap the maximum element with the element at the current position
        arr[i], arr[max_index] = arr[max_index], arr[i]
    return arr