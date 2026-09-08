def extract_even(mixed_tuple):
    # Initialize an empty list to store even elements
    even_elements = []
    # Iterate through each element in the mixed_tuple
    for element in mixed_tuple:
        # Check if the element is an integer
        if isinstance(element, int):
            # Check if the element is even
            if element % 2 == 0:
                # If it is even, append it to the even_elements list
                even_elements.append(element)
    # Return the list of even elements
    return even_elements