def Split(lst):
    # Initialize an empty list to store odd numbers
    odd_numbers = []
    # Iterate through each number in the input list
    for num in lst:
        # Check if the number is odd
        if num % 2 != 0:
            # Append the odd number to the list
            odd_numbers.append(num)
    # Return the list of odd numbers
    return odd_numbers