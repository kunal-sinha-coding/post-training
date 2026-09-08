def remove_odd(numbers):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each number in the input list
    for num in numbers:
        # Check if the number is odd
        if num % 2 != 0:
            # If it is odd, append it to the result list
            result.append(num)
    # Return the result list containing only odd numbers
    return result