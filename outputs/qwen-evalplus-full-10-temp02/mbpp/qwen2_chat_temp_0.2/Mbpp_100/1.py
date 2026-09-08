def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate the digits
    str_n = str(n)
    # Reverse the string to find the smallest palindrome
    str_n = str_n[::-1]
    # Check if the reversed string is a palindrome
    if str_n == str_n[::-1]:
        # If it is, return the original number plus 1
        return n + 1
    # If not, return the next palindrome by incrementing the last digit
    return int(str_n[:-1]) + 1