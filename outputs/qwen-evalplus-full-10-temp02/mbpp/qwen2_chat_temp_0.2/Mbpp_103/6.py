def eulerian_num(n, m):
    """
    Calculate the Eulerian number a(n, m).
    
    Args:
    n (int): The number of vertices.
    m (int): The number of edges.
    
    Returns:
    int: The Eulerian number a(n, m).
    """
    # Base case: Eulerian number for 0 vertices and 0 edges is 1
    if n == 0 and m == 0:
        return 1
    
    # Initialize the result to 0
    result = 0
    
    # Calculate the Eulerian number using the formula
    for i in range(1, n + 1):
        result += i * eulerian_num(i - 1, m)
    
    return result