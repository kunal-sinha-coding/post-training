def heap_sort(arr):
    # Build a max-heap from the input array
    n = len(arr)
    for i in range(n // 2, -1, -1):
        heapify(arr, i)
    
    # Extract elements from the heap one by one
    for i in range(n - 1, 0, -1):
        # Swap the root (maximum) with the last element
        arr[i], arr[0] = arr[0], arr[i]
        # Call heapify on the reduced array
        heapify(arr, 0)
    
    return arr

def heapify(arr, i):
    # Find the largest element in the subtree rooted at index i
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    
    # If left child is greater than root
    if left < n and arr[left] > arr[largest]:
        largest = left
    
    # If right child is greater than largest
    if right < n and arr[right] > arr[largest]:
        largest = right
    
    # If largest is not the root, swap it with the largest element
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        # Recursively heapify the affected subtree
        heapify(arr, largest)