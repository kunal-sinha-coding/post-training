def min_k(tuples_list, k):
    # Sort the tuples based on the second element in descending order
    sorted_tuples = sorted(tuples_list, key=lambda x: x[1], reverse=True)
    # Return the first k elements from the sorted list
    return sorted_tuples[:k]
