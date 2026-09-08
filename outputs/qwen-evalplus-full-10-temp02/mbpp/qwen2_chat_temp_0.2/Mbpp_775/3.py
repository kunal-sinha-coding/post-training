def odd_position(lst):
    # Initialize a flag to check if all odd indices have odd numbers
    flag = True
    # Iterate over the list starting from the second element (index 1)
    for i in range(1, len(lst), 2):
        # Check if the current element is odd
        if lst[i] % 2 == 0:
            # If any odd number is found, set the flag to False
            flag = False
    # Return the flag indicating whether all odd indices have odd numbers
    return flag