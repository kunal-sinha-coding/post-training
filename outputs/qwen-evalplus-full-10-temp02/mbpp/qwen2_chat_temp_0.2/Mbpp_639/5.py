def sample_nam(names):
    # Use list comprehension to filter out names that start with a lowercase letter
    filtered_names = [name for name in names if not name.startswith(name.lower())]
    # Calculate the length of the remaining names
    length = len(filtered_names)
    # Return the total length of the names
    return length