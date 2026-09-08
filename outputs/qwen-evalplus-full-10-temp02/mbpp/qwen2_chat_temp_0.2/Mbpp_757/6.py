def count_reverse_pairs(strings):
    # Initialize a counter for pairs
    count = 0
    # Iterate through each string in the list
    for i in range(len(strings)):
        # Iterate through each string in the list again
        for j in range(i + 1, len(strings)):
            # Check if the reverse of the current string is present in the list
            if strings[j][::-1] in strings:
                count += 1
    return count