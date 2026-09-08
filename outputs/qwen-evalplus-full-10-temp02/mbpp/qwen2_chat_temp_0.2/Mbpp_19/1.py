def test_duplicate(arr):
    # Create a set to store unique elements
    seen = set()
    # Iterate through each element in the array
    for num in arr:
        # Check if the element is already in the set
        if num in seen:
            return True
        # Add the element to the set
        seen.add(num)
    # If no duplicates were found, return False
    return False