def extract_values(s):
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Iterate through each character in the string
    for char in s:
        # Check if the character is a quotation mark
        if char == '"':
            # If it is, append the substring from the current position to the end of the string
            extracted_values.append(s[char:])
    # Return the list of extracted values
    return extracted_values