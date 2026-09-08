def sum_negativenum(numbers):
    # Initialize the sum to 0
    total_sum = 0
    # Flag to check if there are any negative numbers
    has_negative = False
    # Iterate through each number in the list
    for num in numbers:
        # Check if the number is negative
        if num < 0:
            # Add the negative number to the total sum
            total_sum += num
            # Set the flag to True to indicate there are negative numbers
            has_negative = True
    # If there were no negative numbers, return 0
    if not has_negative:
        return 0
    # Return the total sum of negative numbers
    return total_sum