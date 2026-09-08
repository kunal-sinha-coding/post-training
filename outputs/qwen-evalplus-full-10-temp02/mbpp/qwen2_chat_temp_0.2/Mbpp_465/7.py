def drop_empty(dictionary):
    # Use a dictionary comprehension to filter out empty values
    return {key: value for key, value in dictionary.items() if value is not None}