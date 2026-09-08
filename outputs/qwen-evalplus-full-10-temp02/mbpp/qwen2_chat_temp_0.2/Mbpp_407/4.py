def rearrange_bigger(n):
    # Convert the number to a string to easily manipulate the digits
    num_str = str(n)
    # Find the index where the digit is smaller than the next digit
    for i in range(len(num_str) - 2, -1, -1):
        if num_str[i] < num_str[i + 1]:
            # Find the smallest digit to swap with the current digit
            min_index = i + 1
            # Swap the digits
            num_str[i], num_str[min_index] = num_str[min_index], num_str[i]
            # Convert the string back to an integer
            return int(''.join(num_str))
    # If no such pair exists, return the number as is
    return n
