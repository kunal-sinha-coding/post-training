def expensive_items(dataset, n):
    # Sort the dataset by price in descending order
    sorted_dataset = sorted(dataset, key=lambda x: x['price'], reverse=True)
    # Return the first n items from the sorted dataset
    return sorted_dataset[:n]