def smallest_num(numbers):
    # Initialize the smallest number with the first element of the list
    smallest = numbers[0]
    # Iterate through each number in the list
    for num in numbers:
        # Update the smallest number if a smaller number is found
        if num < smallest:
            smallest = num
    # Return the smallest number found
    return smallest