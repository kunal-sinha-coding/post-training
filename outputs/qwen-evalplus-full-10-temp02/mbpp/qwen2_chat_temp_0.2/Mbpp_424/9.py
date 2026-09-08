def extract_rear(string_tuple):
    # Initialize an empty list to store the rear index elements
    rear_elements = []
    # Iterate over each string in the tuple
    for string in string_tuple:
        # Extract the last character of the string
        rear_element = string[-1]
        # Append the rear element to the list
        rear_elements.append(rear_element)
    # Return the list of rear index elements
    return rear_elements
