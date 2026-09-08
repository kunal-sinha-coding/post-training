def min_k(tuples_list, k):
    # Sort the tuples based on the second element of each tuple
    sorted_tuples = sorted(tuples_list, key=lambda x: x[1])
    # Return the first k elements from the sorted list
    return sorted_tuples[:k]
