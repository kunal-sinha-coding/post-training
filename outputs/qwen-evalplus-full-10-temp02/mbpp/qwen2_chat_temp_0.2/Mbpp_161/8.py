# Define the function to remove elements from one list that are present in another list
def remove_elements(list1, list2):
    # Use list comprehension to filter out elements from list1 that are present in list2
    return [x for x in list1 if x not in list2]
