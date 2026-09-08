def pancake_sort(arr):
    n = len(arr)
    for i in range(n-1):
        # Find the maximum element in the unsorted part of the array
        max_index = i
        for j in range(i+1, n):
            if arr[j] > arr[max_index]:
                max_index = j
        # Swap the maximum element with the first element of the unsorted part
        arr[i], arr[max_index] = arr[max_index], arr[i]
        # Reverse the sublist from the current index to the end
        arr[i+1:] = arr[i+1:][::-1]
    return arr
