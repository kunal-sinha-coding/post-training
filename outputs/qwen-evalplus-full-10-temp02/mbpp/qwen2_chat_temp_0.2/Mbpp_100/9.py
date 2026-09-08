def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate the digits
    str_n = str(n)
    # Check if the number is already a palindrome
    if str_n == str_n[::-1]:
        return n  # Return the number as is if it's already a palindrome
    # Find the smallest digit that is greater than the last digit
    for i in range(len(str_n) - 1, -1, -1):
        if str_n[i] > str_n[-1]:
            # Swap the digit with the last digit
            str_n[i], str_n[-1] = str_n[-1], str_n[i]
            # Convert the string back to an integer
            return int(''.join(str_n))
    # If no such digit is found, return the next number after n
    return n + 1