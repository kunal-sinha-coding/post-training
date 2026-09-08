def heap_queue_largest(numbers, n):
    # Sort the list in descending order
    sorted_numbers = sorted(numbers, reverse=True)
    # Return the first n elements of the sorted list
    return sorted_numbers[:n]