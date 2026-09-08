def pancake_sort(arr):
    n = len(arr)
    for i in range(n-1):
        max_index = i
        for j in range(i+1, n):
            if arr[j] > arr[max_index]:
                max_index = j
        arr[i], arr[max_index] = arr[max_index], arr[i]
    return arr