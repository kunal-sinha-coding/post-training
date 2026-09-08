def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate the digits
    str_n = str(n)
    # Start from the second last digit and move to the first digit
    for i in range(len(str_n) - 2, -1, -1):
        # Check if the current digit is greater than the next digit
        if int(str_n[i]) > int(str_n[i + 1]):
            # Swap the digits
            str_n[i], str_n[i + 1] = str_n[i + 1], str_n[i]
            # Convert the string back to an integer
            return int(''.join(str_n))
    # If no such palindrome is found, return the original number
    return n
