def filter_data(data, min_height, min_weight):
    """
    Filters students based on height and weight above the minimum values.
    
    Parameters:
    data (dict): A dictionary where keys are student names and values are tuples of (height, weight).
    min_height (float): The minimum height to filter students by.
    min_weight (float): The minimum weight to filter students by.
    
    Returns:
    dict: A dictionary containing only the students whose height and weight are above the specified minimum values.
    """
    # Filter students based on height and weight
    filtered_data = {name: (height, weight) for name, (height, weight) in data.items() if height > min_height and weight > min_weight}
    return filtered_data
