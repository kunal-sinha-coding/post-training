def larg_nnum(lst, n):
    # Sort the list in descending order
    lst.sort(reverse=True)
    # Return the first n elements from the sorted list
    return lst[:n]