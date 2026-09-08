def count_reverse_pairs(lst):
    # Initialize a counter for pairs
    count = 0
    # Iterate through the list of strings
    for i in range(len(lst)):
        # Iterate through the list of strings starting from the next index
        for j in range(i + 1, len(lst)):
            # Check if the reverse of the current string is present in the list
            if lst[i][::-1] in lst[j]:
                count += 1
    # Return the total count of pairs
    return count