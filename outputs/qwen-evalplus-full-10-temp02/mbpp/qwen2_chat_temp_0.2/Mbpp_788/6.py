# Define the function to create a new tuple from the given string and list
def new_tuple(string_list, string):
    # Use the tuple() constructor to create a tuple from the string and list
    new_tuple = tuple(string_list + [string])
    return new_tuple
