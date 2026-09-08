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
        # Calculate the number of ways to choose i edges from m edges
        ways = m * (m - i + 1) // 2
        # Add the number of ways to choose i edges from n-i edges
        result += ways * i
    
    return result