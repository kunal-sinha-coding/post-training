def eulerian_num(n, m):
    """
    Calculate the Eulerian number a(n, m).
    
    Args:
    n (int): The number of vertices in the graph.
    m (int): The number of edges in the graph.
    
    Returns:
    int: The Eulerian number a(n, m).
    """
    # Initialize the Eulerian number to 0
    eulerian = 0
    
    # Calculate the Eulerian number using the formula
    eulerian = (n + m) * (n - m) // 2
    
    return eulerian