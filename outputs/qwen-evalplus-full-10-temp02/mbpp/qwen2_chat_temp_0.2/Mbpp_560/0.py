def union_elements(tuple1, tuple2):
    # Convert tuples to sets to remove duplicates and then find the union
    set1 = set(tuple1)
    set2 = set(tuple2)
    union_set = set1.union(set2)
    # Convert the union set back to a tuple and sort it
    sorted_union = tuple(sorted(union_set))
    return sorted_union
