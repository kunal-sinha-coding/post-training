def rearrange_bigger(num):
    # Convert the number to a string to easily manipulate its digits
    num_str = str(num)
    # Find the last occurrence of the digit that is smaller than the next digit
    for i in range(len(num_str) - 2, -1, -1):
        if num_str[i] < num_str[i + 1]:
            # Extract the part of the string before the digit that is smaller
            before_digit = num_str[:i]
            # Extract the part of the string after the digit that is smaller
            after_digit = num_str[i + 1:]
            # Sort the digits in the part before the digit that is smaller
            before_digit_sorted = sorted(before_digit)
            # Concatenate the sorted part before the digit, the smaller digit, and the sorted part after the digit
            return int(before_digit_sorted + num_str[i + 1:] + after_digit)
    # If no such digit exists, return the number as is
    return num
