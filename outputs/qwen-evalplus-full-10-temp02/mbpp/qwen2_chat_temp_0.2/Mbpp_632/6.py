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
        # Move the left pointer to the right until it finds a non-zero element
        while left <= right and nums[left] == 0:
            left += 1
        # Move the right pointer to the left until it finds a non-zero element
        while left <= right and nums[right] != 0:
            right -= 1
        # Swap the elements at the left and right pointers
        nums[left], nums[right] = nums[right], nums[left]
    
    return nums