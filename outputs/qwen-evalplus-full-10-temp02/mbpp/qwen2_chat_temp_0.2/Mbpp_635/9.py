def heap_sort(arr):
    # Build a max-heap from the input array
    heapify(arr)
    # Extract elements from the heap and sort them
    sorted_arr = []
    while arr:
        # Extract the maximum element
        max_val = heappop(arr)
        # Append it to the sorted array
        sorted_arr.append(max_val)
    return sorted_arr