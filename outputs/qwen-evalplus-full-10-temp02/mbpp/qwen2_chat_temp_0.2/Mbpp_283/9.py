def validate(n):
    # Convert the number to a string to iterate over each digit
    num_str = str(n)
    # Initialize a dictionary to store the frequency of each digit
    digit_freq = {}
    
    # Iterate over each character in the string representation of the number
    for digit in num_str:
        # Increment the frequency of the current digit in the dictionary
        if digit in digit_freq:
            digit_freq[digit] += 1
        else:
            digit_freq[digit] = 1
    
    # Check if the frequency of each digit is less than or equal to the digit itself
    for freq in digit_freq.values():
        if freq > freq:
            return False
    
    # If all frequencies are less than or equal to the digit itself, return True
    return True