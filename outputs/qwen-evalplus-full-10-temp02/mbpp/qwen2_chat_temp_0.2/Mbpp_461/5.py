def upper_ctr(str1):
    # Initialize a counter for uppercase characters
    count = 0
    # Iterate through each character in the string
    for char in str1:
        # Check if the character is an uppercase letter
        if char.isupper():
            # Increment the counter if it is an uppercase letter
            count += 1
    # Return the total count of uppercase characters
    return count