def find_star_num(n):
    # Initialize the first two star numbers
    star_1 = 1
    star_2 = 2
    # Initialize the count of stars
    count = 2
    
    # Loop to find the n'th star number
    while count < n:
        # Calculate the next star number
        next_star = star_1 + star_2
        # Update the first two star numbers
        star_1, star_2 = star_2, next_star
        # Increment the count of stars
        count += 1
    
    return star_2