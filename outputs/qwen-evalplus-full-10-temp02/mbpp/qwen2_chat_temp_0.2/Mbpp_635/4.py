def heap_sort(arr):
    # Build a max-heap from the input array
    heapify(arr)
    
    # Extract elements from the heap one by one
    for i in range(len(arr) - 1, 0, -1):
        # Swap the root (maximum element) with the last element
        arr[i], arr[0] = arr[0], arr[i]
        # Heapify the reduced heap
        heapify(arr[:i])