def heap_queue_largest(numbers, n):
    # Create a max-heap from the list of numbers
    heap = numbers[:]
    heapq.heapify(heap)
    
    # Extract the n largest elements from the heap
    largest_elements = [heapq.heappop(heap) for _ in range(n)]
    
    # Return the largest n elements in descending order
    return largest_elements[::-1]