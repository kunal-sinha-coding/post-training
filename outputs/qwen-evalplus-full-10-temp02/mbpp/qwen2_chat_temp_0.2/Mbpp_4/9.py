def heap_queue_largest(numbers, n):
    # Convert the list to a heap
    heapq.heapify(numbers)
    # Extract the n largest elements from the heap
    largest_elements = heapq.nlargest(n, numbers)
    # Return the largest elements in descending order
    return largest_elements[::-1]