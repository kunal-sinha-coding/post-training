def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate digits
    str_n = str(n)
    # Iterate through the string from the second last character to the first character
    for i in range(len(str_n) - 2, -1, -1):
        # Check if the current character is greater than the next character
        if str_n[i] > str_n[i + 1]:
            # Extract the part of the string before the current character
            part1 = str_n[:i]
            # Extract the part of the string after the current character
            part2 = str_n[i + 1:]
            # Reverse the part2 to form the new palindrome
            part2 = part2[::-1]
            # Concatenate the parts to form the new palindrome
            new_palindrome = part1 + part2
            # Convert the new palindrome back to an integer
            return int(new_palindrome)
    # If no such palindrome is found, return the original number
    return n