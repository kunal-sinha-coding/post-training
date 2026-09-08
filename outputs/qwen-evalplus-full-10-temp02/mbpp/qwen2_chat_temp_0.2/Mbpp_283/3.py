def validate(n):
    # Convert the number to a string to iterate over each digit
    str_n = str(n)
    # Initialize a dictionary to store the frequency of each digit
    digit_freq = {}
    # Iterate over each character in the string representation of the number
    for char in str_n:
        # If the character is already in the dictionary, increment its count
        if char in digit_freq:
            digit_freq[char] += 1
        # If the character is not in the dictionary, add it with a count of 1
        else:
            digit_freq[char] = 1
    # Check if all digit frequencies are less than or equal to the digit itself
    for freq in digit_freq.values():
        if freq > freq:
            return False
    return True