def consecutive_duplicates(lst):
    # Initialize an empty list to store unique elements
    unique_lst = []
    # Iterate through each element in the input list
    for i in range(len(lst)):
        # Check if the current element is not the same as the previous one
        if lst[i] != lst[i - 1]:
            # If not, append the current element to the unique list
            unique_lst.append(lst[i])
    # Return the list of unique elements
    return unique_lst