def Split(numbers):
    # Initialize an empty list to store odd numbers
    odd_numbers = []
    # Iterate through each number in the input list
    for number in numbers:
        # Check if the number is odd
        if number % 2 != 0:
            # Append the odd number to the list
            odd_numbers.append(number)
    # Return the list of odd numbers
    return odd_numbers