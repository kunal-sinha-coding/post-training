def rearrange_bigger(n):
    # Convert the number to a string to easily manipulate digits
    num_str = str(n)
    # Find the index of the first digit that is smaller than the next digit
    for i in range(len(num_str) - 1):
        if num_str[i] < num_str[i + 1]:
            # Find the smallest digit to swap with the current digit
            min_index = i + 1
            # Swap the digits
            num_str[i], num_str[min_index] = num_str[min_index], num_str[i]
            # Convert the string back to an integer
            return int(num_str)
    # If no such digit exists, the number is already the largest, so return -1
    return -1