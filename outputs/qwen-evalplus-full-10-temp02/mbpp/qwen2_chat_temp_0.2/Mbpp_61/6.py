def count_Substrings(s):
    # Initialize the count of substrings with the sum of digits equal to their length
    count = 0
    
    # Iterate through each character in the string
    for i in range(len(s)):
        # Calculate the sum of digits for the current substring
        current_sum = sum(int(digit) for digit in s[i:])
        
        # Check if the current sum is equal to the length of the substring
        if current_sum == len(s):
            count += 1
    
    return count