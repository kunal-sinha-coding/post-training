def min_k(tuples_list, k):
    # Sort the tuples based on the second element in descending order
    tuples_list.sort(key=lambda x: x[1], reverse=True)
    # Return the first k elements from the sorted list
    return tuples_list[:k]
