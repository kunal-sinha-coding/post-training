def rotate_right(lst, n):
    # Calculate the effective rotation needed
    effective_rotation = n % len(lst)
    # Perform the rotation
    lst = lst[-effective_rotation:] + lst[:-effective_rotation]
    return lst