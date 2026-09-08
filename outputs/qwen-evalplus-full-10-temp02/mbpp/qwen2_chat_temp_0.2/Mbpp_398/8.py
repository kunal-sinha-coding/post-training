def sum_of_digits(numbers):
    """
    Compute the sum of digits of each number in a given list.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The sum of digits of all numbers in the list.
    """
    total_sum = 0
    for number in numbers:
        # Convert the number to a string to iterate over each digit
        for digit in str(number):
            # Convert the digit back to an integer and add it to the total sum
            total_sum += int(digit)
    return total_sum
