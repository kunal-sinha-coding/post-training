def check_element(lst, element):
    """
    Check if all items in the list are equal to the given element.

    Args:
    lst (list): The list to check.
    element (any): The element to compare against.

    Returns:
    bool: True if all items in the list are equal to the given element, False otherwise.
    """
    # Check if all elements in the list are equal to the given element
    return all(x == element for x in lst)