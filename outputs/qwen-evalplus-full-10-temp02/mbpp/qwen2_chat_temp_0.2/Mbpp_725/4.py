def extract_quotation(input_string):
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is a quotation mark
        if char == '"':
            # Append the extracted value to the list
            extracted_values.append(char)
    # Return the list of extracted values
    return extracted_values