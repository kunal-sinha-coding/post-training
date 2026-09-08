def recursive_list_sum(lst):
    # Base case: if the list is empty, return 0
    if not lst:
        return 0
    # Recursive case: sum the first element of the list and the result of the recursive call on the rest of the list
    return lst[0] + recursive_list_sum(lst[1:])
