def filter_data(data, min_height, min_weight):
    """
    Filters students based on their height and weight being above the specified minimum values.
    
    Parameters:
    - data (dict): A dictionary where keys are student names and values are tuples of (height, weight).
    - min_height (float): The minimum height a student must have to be included in the result.
    - min_weight (float): The minimum weight a student must have to be included in the result.
    
    Returns:
    - dict: A dictionary containing only the students whose height and weight are above the specified minimum values.
    """
    # Filter the dictionary to include only students with height and weight above the minimum values
    filtered_data = {name: value for name, (height, weight) in data.items() if height > min_height and weight > min_weight}
    return filtered_data
