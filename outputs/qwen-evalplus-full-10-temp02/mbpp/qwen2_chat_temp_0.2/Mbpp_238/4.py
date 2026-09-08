def number_of_substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Iterate through each character in the substring starting from the current character
        for j in range(i, len(s)):
            # Append the substring to the count
            count += 1
    return count