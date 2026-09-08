def split_two_parts(lst, L):
    # Split the list into two parts
    first_part = lst[:L]
    second_part = lst[L:]
    # Return the resulting lists in a tuple
    return (first_part, second_part)