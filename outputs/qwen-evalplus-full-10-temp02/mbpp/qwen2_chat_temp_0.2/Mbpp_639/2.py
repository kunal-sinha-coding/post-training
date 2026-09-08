# Define the function to calculate the sum of names after removing those starting with a lowercase letter
def sample_nam(names):
    # Use list comprehension to filter out names that start with a lowercase letter
    filtered_names = [name for name in names if not name.startswith('a')]
    # Calculate the sum of the lengths of the remaining names
    total_length = sum(len(name) for name in filtered_names)
    return total_length
