def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate the digits
    str_n = str(n)
    # Check if the number is already a palindrome
    if str_n == str_n[::-1]:
        return n  # Return the number as is, since it's already a palindrome
    # If the number is not a palindrome, find the smallest palindrome by reversing the first half and adding 1
    for i in range(len(str_n)):
        # Check if the first half of the number is greater than the middle digit
        if str_n[:i] > str_n[i + 1]:
            # Reverse the first half and add 1
            return int(str_n[:i][::-1] + '1')
    # If no palindrome is found, return the next number after n
    return n + 1
