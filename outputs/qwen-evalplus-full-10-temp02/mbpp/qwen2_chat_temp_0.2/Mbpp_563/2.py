def extract_values(s):
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Iterate through each character in the string
    for char in s:
        # Check if the character is a quotation mark
        if char == '"':
            # Append the value to the list
            extracted_values.append(char)
    # Return the list of extracted values
    return extracted_values