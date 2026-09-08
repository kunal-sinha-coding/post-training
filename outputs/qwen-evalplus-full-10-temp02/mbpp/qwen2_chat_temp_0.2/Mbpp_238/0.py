def number_of_substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Iterate through each character after the current character
        for j in range(i + 1, len(s) + 1):
            # Append the substring from i to j to the count
            count += 1
    return count