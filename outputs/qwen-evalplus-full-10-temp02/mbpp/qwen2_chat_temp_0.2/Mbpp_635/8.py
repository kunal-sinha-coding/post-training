def heap_sort(arr):
    # Build a max heap
    for i in range(len(arr)):
        heapify(arr, i)
    
    # Extract elements from the heap
    for i in range(len(arr) - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        heapify(arr, 0)