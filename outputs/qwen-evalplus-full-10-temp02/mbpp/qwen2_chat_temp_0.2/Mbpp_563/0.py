def extract_values(input_string):
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Use a loop to iterate through each character in the input string
    for char in input_string:
        # Check if the character is a quote mark
        if char == '"':
            # Append the character to the list of extracted values
            extracted_values.append(char)
    # Return the list of extracted values
    return extracted_values