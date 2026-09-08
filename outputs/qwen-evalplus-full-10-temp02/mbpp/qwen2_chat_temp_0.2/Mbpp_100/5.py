def next_smallest_palindrome(n):
    # Convert the number to a string to easily iterate over each digit
    str_n = str(n)
    # Iterate over the string from the second last character to the first character
    for i in range(len(str_n) - 2, -1, -1):
        # Check if the current character is greater than the next character
        if str_n[i] > str_n[i + 1]:
            # Find the smallest digit greater than the current character
            for j in range(i + 1, len(str_n)):
                if str_n[j] < str_n[i]:
                    # Swap the characters
                    str_n[i], str_n[j] = str_n[j], str_n[i]
                    # Convert the string back to an integer
                    return int(''.join(str_n))
    # If no such palindrome is found, return the original number
    return n