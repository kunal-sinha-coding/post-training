# Define the function to count positive numbers in a list
def pos_count(numbers):
    # Initialize a counter for positive numbers
    count = 0
    # Iterate through each number in the list
    for number in numbers:
        # Check if the number is positive
        if number > 0:
            # Increment the counter if the number is positive
            count += 1
    # Return the total count of positive numbers
    return count
