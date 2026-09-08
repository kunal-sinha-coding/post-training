def filter_data(student_data, min_height, min_weight):
    # Filter students whose height and weight are above the minimum values
    filtered_students = {name: (height, weight) for name, (height, weight) in student_data.items() if height > min_height and weight > min_weight}
    return filtered_students