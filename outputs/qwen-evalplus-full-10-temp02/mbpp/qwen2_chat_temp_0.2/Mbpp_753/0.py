def min_k(tuples_list, k):
    # Sort the tuples based on the second element in ascending order
    tuples_list.sort(key=lambda x: x[1])
    # Return the first k elements from the sorted list
    return tuples_list[:k]
