def first_odd(numbers):
    # Iterate through the list to find the first odd number
    for num in numbers:
        if num % 2 != 0:
            return num
    # If no odd number is found, return None
    return None