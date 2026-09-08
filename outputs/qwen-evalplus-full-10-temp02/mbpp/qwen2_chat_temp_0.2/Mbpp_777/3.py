def find_sum(numbers):
    # Initialize the sum to 0
    total_sum = 0
    # Create a set to store unique numbers
    unique_numbers = set(numbers)
    # Iterate through each number in the set
    for number in unique_numbers:
        # Add the number to the total sum
        total_sum += number
    # Return the total sum of non-repeated elements
    return total_sum