def check_element(lst, element):
    # Check if all elements in the list are equal to the given element
    return all(x == element for x in lst)