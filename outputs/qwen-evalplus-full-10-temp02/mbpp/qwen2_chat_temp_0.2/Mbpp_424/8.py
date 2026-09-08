# Define the function to extract the rear index element of each string in the tuple
def extract_rear(strings):
    # Use list comprehension to iterate over each string in the tuple
    return [strings[i][-1] for i in range(len(strings))]
