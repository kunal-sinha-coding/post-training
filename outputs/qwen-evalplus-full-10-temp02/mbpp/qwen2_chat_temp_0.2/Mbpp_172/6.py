# Define the function to count the number of 'std' in a given string
def count_occurance(input_string):
    # Initialize a counter to keep track of the number of 'std'
    count = 0
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the current character is 'std'
        if char == 'std':
            # Increment the counter if it is
            count += 1
    # Return the total count of 'std'
    return count