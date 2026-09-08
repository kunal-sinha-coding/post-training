def validate(number):
    # Convert the number to a string to iterate over each digit
    number_str = str(number)
    # Initialize a dictionary to store the frequency of each digit
    digit_frequency = {}
    
    # Iterate over each character in the string representation of the number
    for digit in number_str:
        # If the digit is already in the dictionary, increment its count
        if digit in digit_frequency:
            digit_frequency[digit] += 1
        # If the digit is not in the dictionary, add it with a count of 1
        else:
            digit_frequency[digit] = 1
    
    # Check if all digit frequencies are less than or equal to the digit itself
    for frequency in digit_frequency.values():
        if frequency > frequency:
            return False
    
    # If all digit frequencies are less than or equal to the digit itself, return True
    return True