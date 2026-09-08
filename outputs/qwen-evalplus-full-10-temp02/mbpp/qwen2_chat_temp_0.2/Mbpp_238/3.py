def number_of_substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate over each character in the string
    for i in range(len(s)):
        # Iterate over each possible starting point for a substring
        for j in range(i + 1, len(s) + 1):
            # Append the substring to the count
            count += 1
    # Return the total count of substrings
    return count