# Define the function to extract the nth element from a list of tuples
def extract_nth_element(tuples_list, n):
    # Use list comprehension to extract the nth element from each tuple
    nth_element = [t[n] for t in tuples_list]
    return nth_element
