def filter_data(student_data, min_height, min_weight):
    """
    This function filters students based on their height and weight.
    
    Parameters:
    student_data (dict): A dictionary where keys are student names and values are tuples of (height, weight).
    min_height (float): The minimum height for a student to be included in the result.
    min_weight (float): The minimum weight for a student to be included in the result.
    
    Returns:
    dict: A dictionary containing only the students whose height and weight are above the specified minimum values.
    """
    # Filter students based on height and weight
    filtered_students = {name: (height, weight) for name, (height, weight) in student_data.items() if height > min_height and weight > min_weight}
    return filtered_students
