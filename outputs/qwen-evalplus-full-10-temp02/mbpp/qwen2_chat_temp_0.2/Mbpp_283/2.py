def validate(n):
    # Convert the number to a string to iterate over each digit
    num_str = str(n)
    # Initialize a dictionary to store the frequency of each digit
    digit_freq = {}
    # Iterate over each character in the string representation of the number
    for digit in num_str:
        # If the digit is already in the dictionary, increment its count
        if digit in digit_freq:
            digit_freq[digit] += 1
        # If the digit is not in the dictionary, add it with a count of 1
        else:
            digit_freq[digit] = 1
    # Iterate over the dictionary to check if each digit's frequency is less than or equal to the digit itself
    for digit, freq in digit_freq.items():
        if freq > digit:
            return False
    # If all digits' frequencies are less than or equal to the digit itself, return True
    return True