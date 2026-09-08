def merge_dictionaries_three(dict1, dict2, dict3):
    """
    Merge three dictionaries into a single dictionary.
    
    Parameters:
    dict1 (dict): The first dictionary to merge.
    dict2 (dict): The second dictionary to merge.
    dict3 (dict): The third dictionary to merge.
    
    Returns:
    dict: A single dictionary containing all key-value pairs from all three input dictionaries.
    """
    # Using the update method to merge the dictionaries
    merged_dict = dict1.copy()
    merged_dict.update(dict2)
    merged_dict.update(dict3)
    return merged_dict
