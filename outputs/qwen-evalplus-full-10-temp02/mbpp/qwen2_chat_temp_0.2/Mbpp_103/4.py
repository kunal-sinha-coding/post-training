def eulerian_num(n, m):
    """
    Calculate the Eulerian number a(n, m).
    
    Args:
    n (int): The number of vertices.
    m (int): The number of edges.
    
    Returns:
    int: The Eulerian number a(n, m).
    """
    # Base case: Eulerian number for n=0 is 1
    if n == 0:
        return 1
    
    # Initialize the result to 0
    result = 0
    
    # Calculate the Eulerian number iteratively
    for i in range(1, n + 1):
        # Calculate the number of edges from vertex i to vertex j
        edges = m * (n - i)
        # Add the number of edges to the result
        result += edges
    
    return result