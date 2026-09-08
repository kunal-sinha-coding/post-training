def combinations_colors(colors, n):
    # Initialize an empty list to store the combinations
    combinations = []
    # Iterate through each possible combination of n elements from the list
    for i in range(len(colors)):
        # Generate all combinations of n elements from the list
        for j in range(i + 1, len(colors) + 1):
            # Append the combination as a tuple to the list
            combinations.append(tuple(colors[i:j]))
    # Return the list of combinations
    return combinations