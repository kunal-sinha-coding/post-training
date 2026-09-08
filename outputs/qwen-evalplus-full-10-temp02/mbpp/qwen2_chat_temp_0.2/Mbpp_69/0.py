# Define the function to check if a list contains a sublist
def is_sublist(main_list, sub_list):
    # Check if the main list is empty
    if not main_list:
        return False
    # Iterate through the main list to check for the sub_list
    for i in range(len(main_list)):
        # Check if the current element in the main list matches the first element of the sub_list
        if main_list[i] == sub_list[0]:
            # Check if the remaining elements in the main list match the rest of the sub_list
            if main_list[i:i+len(sub_list)] == sub_list:
                return True
    # If no match is found, return False
    return False