def rotate_right(lst, n):
    # Calculate the effective number of rotations needed
    effective_n = n % len(lst)
    # Perform the rotation
    lst = lst[-effective_n:] + lst[:-effective_n]
    return lst