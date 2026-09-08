def remove_odd(numbers):
    # Initialize an empty list to store the result
    result = []
    # Flag to check if there are any odd numbers
    has_odd = False
    # Iterate through each number in the input list
    for num in numbers:
        # Check if the number is odd
        if num % 2 != 0:
            # If it's odd, add it to the result list
            result.append(num)
            has_odd = True
    # If there were no odd numbers, return an empty list
    if not has_odd:
        return []
    # Return the result list with odd numbers removed
    return result