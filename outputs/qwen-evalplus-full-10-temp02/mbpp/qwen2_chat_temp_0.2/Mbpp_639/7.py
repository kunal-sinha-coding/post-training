def sample_nam(names):
    # Use list comprehension to filter out names starting with a lowercase letter
    filtered_names = [name for name in names if not name.startswith(name[0].lower())]
    # Calculate the sum of the lengths of the remaining names
    total_length = sum(len(name) for name in filtered_names)
    return total_length