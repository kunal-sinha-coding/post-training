# Define the function to find shared elements
def similar_elements(list1, list2):
    # Use set intersection to find common elements
    shared_elements = list(set(list1) & set(list2))
    return shared_elements
