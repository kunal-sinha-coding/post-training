def common_in_nested_lists(nested_lists):
    # Use set intersection to find common elements across all lists
    common_elements = set(nested_lists[0]).intersection(*nested_lists[1:])
    return common_elements
