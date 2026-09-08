# Define the function to check for common elements
def common_element(list1, list2):
    # Use a set to store elements from the first list
    set1 = set(list1)
    # Check if any element from the second list is in the set
    return any(element in set1 for element in list2)
