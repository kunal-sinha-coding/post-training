def filter_data(student_data, min_height, min_weight):
    """
    Filters students whose height and weight are above the specified minimum values.
    
    Parameters:
    student_data (dict): A dictionary where keys are student names and values are tuples of (height, weight).
    min_height (float): The minimum height to filter students by.
    min_weight (float): The minimum weight to filter students by.
    
    Returns:
    dict: A dictionary containing only the students whose height and weight are above the specified minimum values.
    """
    # Filter students based on the minimum height and weight
    filtered_students = {name: (height, weight) for name, (height, weight) in student_data.items() if height > min_height and weight > min_weight}
    return filtered_students
