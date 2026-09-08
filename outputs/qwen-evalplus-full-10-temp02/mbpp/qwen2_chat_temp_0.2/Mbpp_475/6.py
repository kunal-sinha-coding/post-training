def sort_counter(counter):
    # Sort the dictionary by value in ascending order
    sorted_counter = sorted(counter.items(), key=lambda item: item[1])
    return sorted_counter