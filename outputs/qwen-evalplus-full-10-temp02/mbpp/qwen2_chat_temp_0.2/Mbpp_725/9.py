def extract_quotation(input_string):
    """
    Extracts values between quotation marks " " from the given string.
    
    Args:
    input_string (str): The string from which to extract values.
    
    Returns:
    list: A list of extracted values.
    """
    # Initialize an empty list to store the extracted values
    extracted_values = []
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is a quotation mark
        if char == '"':
            # If it is, append the value to the list
            extracted_values.append(char)
    # Return the list of extracted values
    return extracted_values
