def Split(numbers):
    # Initialize an empty list to store even numbers
    even_numbers = []
    # Iterate through each number in the input list
    for number in numbers:
        # Check if the number is even
        if number % 2 == 0:
            # If it is even, append it to the even_numbers list
            even_numbers.append(number)
    # Return the list of even numbers
    return even_numbers