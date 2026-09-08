def remove_nested(tup):
    # Use list comprehension to iterate over each element in the tuple
    # and check if it is a tuple itself
    # If it is, remove it from the list
    # Otherwise, keep it in the list
    return [item for item in tup if not isinstance(item, tuple)]
