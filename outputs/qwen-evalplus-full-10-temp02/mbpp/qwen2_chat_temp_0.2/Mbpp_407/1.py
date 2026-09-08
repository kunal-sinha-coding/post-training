def rearrange_bigger(num):
    # Convert the number to a string to easily manipulate digits
    num_str = str(num)
    # Find the index of the largest digit
    max_index = num_str.index(max(num_str))
    # Swap the largest digit with the second last digit
    num_str[max_index], num_str[-1] = num_str[-1], num_str[max_index]
    # Convert the string back to an integer
    return int(num_str)
