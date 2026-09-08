# Define the function to remove elements from the first list that are present in the second list
def remove_elements(list1, list2):
    # Use list comprehension to filter out elements present in list2 from list1
    result = [item for item in list1 if item not in list2]
    return result
