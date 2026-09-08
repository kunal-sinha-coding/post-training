def validate(n):
    # Convert the integer to a string to iterate over each digit
    str_n = str(n)
    # Initialize a dictionary to store the frequency of each digit
    digit_freq = {}
    # Iterate over each character in the string representation of the number
    for char in str_n:
        # If the character is a digit, increment its frequency in the dictionary
        if char.isdigit():
            if char in digit_freq:
                digit_freq[char] += 1
            else:
                digit_freq[char] = 1
    # Check if all frequencies are less than or equal to the digit itself
    for freq in digit_freq.values():
        if freq > freq:
            return False
    return True