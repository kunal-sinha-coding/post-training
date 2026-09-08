def rotate_right(lst, n):
    # Rotate the list by n items to the right
    lst = lst[-n:] + lst[:-n]
    return lst