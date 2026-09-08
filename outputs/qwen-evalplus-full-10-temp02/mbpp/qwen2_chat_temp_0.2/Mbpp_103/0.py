def eulerian_num(n, m):
    """
    Calculate the Eulerian number a(n, m).
    
    Args:
    n (int): The number of vertices in the graph.
    m (int): The number of edges in the graph.
    
    Returns:
    int: The Eulerian number a(n, m).
    """
    # Base case: Eulerian number for a single vertex is 1
    if n == 1:
        return 1
    
    # Initialize the result to 0
    result = 0
    
    # Calculate the Eulerian number iteratively
    for i in range(1, n + 1):
        # Calculate the number of ways to choose i vertices out of n
        ways = n - i + 1
        # Calculate the number of ways to choose m edges out of i vertices
        edges = m * ways
        # Add the product of ways and edges to the result
        result += ways * edges
    
    return result