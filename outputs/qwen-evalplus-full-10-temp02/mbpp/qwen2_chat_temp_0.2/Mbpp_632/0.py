def move_zeroes(nums):
    """
    Move all zeroes to the end of the given list.
    
    Args:
    nums (list): The list of integers.
    
    Returns:
    list: The list with zeroes moved to the end.
    """
    # Initialize pointers for the start and end of the list
    left = 0
    right = len(nums) - 1
    
    # Traverse the list
    while left <= right:
        # If the current element is not zero, move it to the left
        if nums[left] != 0:
            nums[left], nums[right] = nums[right], nums[left]
            left += 1
        # Move the right pointer to the right if the current element is zero
        right -= 1
    
    return nums