def number_ctr(str1):
    # Initialize a counter to zero
    count = 0
    # Iterate through each character in the string
    for char in str1:
        # Check if the character is a digit
        if char.isdigit():
            # Increment the counter if it is a digit
            count += 1
    # Return the total count of digits
    return count