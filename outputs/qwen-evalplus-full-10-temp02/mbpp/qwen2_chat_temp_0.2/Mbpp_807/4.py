def first_odd(numbers):
    # Iterate through the list of numbers
    for number in numbers:
        # Check if the number is odd
        if number % 2 != 0:
            # Return the first odd number found
            return number
    # If no odd number is found, return None
    return None