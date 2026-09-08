def number_ctr(str1):
    # Initialize a counter for digits
    digit_count = 0
    # Iterate through each character in the string
    for char in str1:
        # Check if the character is a digit
        if char.isdigit():
            # Increment the counter if it is a digit
            digit_count += 1
    # Return the total count of digits
    return digit_count