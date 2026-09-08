def neg_nos(lst):
    # Initialize an empty list to store negative numbers
    neg_list = []
    # Iterate through each number in the input list
    for num in lst:
        # Check if the number is negative
        if num < 0:
            # If it is negative, append it to the neg_list
            neg_list.append(num)
    # Return the list of negative numbers
    return neg_list