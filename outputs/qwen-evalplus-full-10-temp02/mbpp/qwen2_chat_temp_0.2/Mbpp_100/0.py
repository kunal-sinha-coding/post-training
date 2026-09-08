def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate its digits
    str_n = str(n)
    # Check if the number is already a palindrome
    if str_n == str_n[::-1]:
        return n  # Return the number as is if it's already a palindrome
    # Start from the end of the string and move towards the middle
    for i in range(len(str_n) - 1, -1, -1):
        # Check if the current digit is greater than the next digit
        if int(str_n[i]) > int(str_n[i + 1]):
            # Find the smallest digit to swap with the current digit
            for j in range(i + 1, len(str_n)):
                if int(str_n[j]) < int(str_n[i]):
                    # Swap the digits
                    str_n[i], str_n[j] = str_n[j], str_n[i]
                    # Convert the string back to an integer
                    return int(''.join(str_n))
    # If no such pair is found, return the next number after n
    return n + 1