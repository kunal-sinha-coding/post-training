def validate(n):
    # Convert the integer to a string to iterate over each digit
    num_str = str(n)
    # Initialize a dictionary to store the frequency of each digit
    digit_freq = {}
    
    # Iterate over each character in the string
    for digit in num_str:
        # If the digit is already in the dictionary, increment its count
        if digit in digit_freq:
            digit_freq[digit] += 1
        # If the digit is not in the dictionary, add it with a count of 1
        else:
            digit_freq[digit] = 1
    
    # Check if all digit frequencies are less than or equal to the digit itself
    for freq in digit_freq.values():
        if freq > freq:
            return False
    
    # If all digit frequencies are less than or equal to the digit itself, return True
    return True