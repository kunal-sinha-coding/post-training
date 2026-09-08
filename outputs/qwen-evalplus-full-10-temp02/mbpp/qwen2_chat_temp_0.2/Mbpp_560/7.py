def union_elements(tuple1, tuple2):
    # Convert tuples to sets to remove duplicates and then find the union
    union_set = set(tuple1) | set(tuple2)
    # Convert the set back to a list and sort it
    sorted_union = sorted(list(union_set))
    return sorted_union