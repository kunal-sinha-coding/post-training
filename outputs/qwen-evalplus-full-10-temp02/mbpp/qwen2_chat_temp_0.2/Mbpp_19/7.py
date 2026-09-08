def test_duplicate(arr):
    # Create a set to store unique elements
    unique_elements = set(arr)
    # Compare the length of the set with the original array
    return len(unique_elements) == len(arr)