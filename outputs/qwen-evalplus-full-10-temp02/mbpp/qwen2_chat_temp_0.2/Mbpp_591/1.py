def swap_List(lst):
    # Swap the first and last elements of the list
    lst[0], lst[-1] = lst[-1], lst[0]
    return lst