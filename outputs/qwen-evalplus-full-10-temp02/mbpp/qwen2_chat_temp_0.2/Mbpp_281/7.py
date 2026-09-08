def all_unique(lst):
    """
    Check if all elements in the given list are unique.

    Args:
    lst (list): The list to check for uniqueness.

    Returns:
    bool: True if all elements are unique, False otherwise.
    """
    # Convert the list to a set to remove duplicates
    unique_elements = set(lst)
    # Compare the length of the original list with the length of the set
    return len(lst) == len(unique_elements)