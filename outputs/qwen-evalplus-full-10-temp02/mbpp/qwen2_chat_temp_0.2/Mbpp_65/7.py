def recursive_list_sum(lst):
    # Base case: if the list is empty, return 0
    if not lst:
        return 0
    # Recursive case: add the first element of the list to the sum of the rest of the list
    return lst[0] + recursive_list_sum(lst[1:])