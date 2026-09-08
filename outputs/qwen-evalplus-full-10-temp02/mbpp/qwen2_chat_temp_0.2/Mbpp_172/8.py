# Define the function to count the number of 'std' occurrences in a given string
def count_occurance(input_string):
    # Initialize a counter to zero
    count = 0
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is 'std'
        if char == 'std':
            # Increment the counter if 'std' is found
            count += 1
    # Return the total count of 'std' occurrences
    return count
