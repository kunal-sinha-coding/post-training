def remove_odd(numbers):
    # Initialize an empty list to store the result
    result = []
    # Flag to check if there are any odd numbers
    has_odd = False
    # Iterate through each number in the input list
    for num in numbers:
        # Check if the number is odd
        if num % 2 != 0:
            # If it's odd, append it to the result list
            result.append(num)
            # Set the flag to True to indicate there are odd numbers
            has_odd = True
    # If no odd numbers were found, return an empty list
    if not has_odd:
        return []
    # Return the list of odd numbers
    return result