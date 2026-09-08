def number_of_substrings(s):
    # Initialize a counter for the number of substrings
    count = 0
    # Iterate through the string to find all possible substrings
    for i in range(len(s)):
        # Iterate through the substring starting from the current index
        for j in range(i + 1, len(s) + 1):
            # Append the substring to the counter
            count += 1
    # Return the total count of substrings
    return count