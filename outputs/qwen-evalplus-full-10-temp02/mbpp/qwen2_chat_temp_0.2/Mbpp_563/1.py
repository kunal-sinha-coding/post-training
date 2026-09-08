def extract_values(input_string):
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is a quotation mark
        if char == '"':
            # If it is, append the substring between the current character and the next character to the list
            extracted_values.append(input_string[char+1:])
    # Return the list of extracted values
    return extracted_values