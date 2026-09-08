def number_of_substrings(s):
    # Initialize the count of substrings to 0
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Iterate through each character in the substring starting from the current index
        for j in range(i, len(s)):
            # If the substring is non-empty, increment the count
            if s[i:j+1] != "":
                count += 1
    # Return the total count of non-empty substrings
    return count