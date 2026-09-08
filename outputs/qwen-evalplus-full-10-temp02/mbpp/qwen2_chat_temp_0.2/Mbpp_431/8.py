# Define the function to check for common elements
def common_element(list1, list2):
    # Use a set to store elements of the first list
    set1 = set(list1)
    # Iterate through each element in the second list
    for element in list2:
        # Check if the element is in the set of the first list
        if element in set1:
            # Return True if a common element is found
            return True
    # If no common element is found, return False
    return False