def find_tuples(tuples_list, k):
    # Filter tuples where all elements are divisible by k
    divisible_tuples = [t for t in tuples_list if all(x % k == 0 for x in t)]
    return divisible_tuples