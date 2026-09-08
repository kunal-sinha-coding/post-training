def sample_nam(names):
    """
    This function takes a list of names as input and returns the sum of the lengths of the names that do not start with a lowercase letter.
    
    :param names: List of names
    :return: Sum of the lengths of names that do not start with a lowercase letter
    """
    # Filter the names that do not start with a lowercase letter
    filtered_names = [name for name in names if not name.startswith(name.lower())]
    # Calculate the sum of the lengths of the filtered names
    total_length = sum(len(name) for name in filtered_names)
    return total_length