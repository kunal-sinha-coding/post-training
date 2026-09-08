def first_odd(numbers):
    # Iterate through the list and find the first odd number
    for number in numbers:
        if number % 2 != 0:
            return number
    # If no odd number is found, return None
    return None