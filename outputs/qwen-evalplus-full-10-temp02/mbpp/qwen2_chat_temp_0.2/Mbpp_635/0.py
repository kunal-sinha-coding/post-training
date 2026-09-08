def heap_sort(arr):
    # Build a max heap
    for i in range(len(arr)):
        heapify(arr, i)
    
    # Extract elements from the heap
    for i in range(len(arr) - 1, 0, -1):
        # Swap the root with the last element
        arr[i], arr[0] = arr[0], arr[i]
        # Heapify the reduced heap
        heapify(arr, 0)
    
    return arr

def heapify(arr, i):
    # Find the largest element in the subtree rooted at index i
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    
    # If left child is greater than root
    if left < len(arr) and arr[left] > arr[largest]:
        largest = left
    
    # If right child is greater than largest
    if right < len(arr) and arr[right] > arr[largest]:
        largest = right
    
    # If largest is not the root, swap it with the largest element
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        # Heapify the reduced heap
        heapify(arr, largest)