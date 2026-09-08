def test_duplicate(arr):
    # Create a set to store the elements of the array
    seen = set()
    
    # Iterate through each element in the array
    for num in arr:
        # Check if the element is already in the set
        if num in seen:
            # If it is, return True indicating a duplicate
            return True
        # If it's not, add the element to the set
        seen.add(num)
    
    # If no duplicates are found, return False
    return False