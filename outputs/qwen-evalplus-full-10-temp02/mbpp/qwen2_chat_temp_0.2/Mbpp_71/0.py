def comb_sort(arr):
    n = len(arr)
    gap = 1
    while gap < n:
        # Find the minimum element in the unsorted part of the array
        min_index = 0
        for i in range(1, n):
            if arr[i] < arr[min_index]:
                min_index = i
        # Swap the found minimum element with the first element of the unsorted part
        arr[min_index], arr[0] = arr[0], arr[min_index]
        # Reduce the gap by 1
        gap = 2 * gap
    return arr