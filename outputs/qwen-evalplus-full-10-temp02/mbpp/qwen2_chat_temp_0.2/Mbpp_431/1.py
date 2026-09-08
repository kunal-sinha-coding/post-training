# Define the function to check for common elements
def common_element(list1, list2):
    # Use the set intersection method to find common elements
    common = list(set(list1) & set(list2))
    # Return True if there are common elements, otherwise False
    return len(common) > 0
