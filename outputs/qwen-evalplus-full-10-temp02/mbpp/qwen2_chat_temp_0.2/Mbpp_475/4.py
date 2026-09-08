def sort_counter(counter):
    # Sort the dictionary by values in descending order
    sorted_counter = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    return sorted_counter