def consecutive_duplicates(lst):
    # Initialize an empty list to store unique elements
    unique_lst = []
    # Iterate through the list
    for num in lst:
        # If the current number is not the same as the last number in the list, add it to the unique list
        if num != unique_lst[-1]:
            unique_lst.append(num)
    return unique_lst