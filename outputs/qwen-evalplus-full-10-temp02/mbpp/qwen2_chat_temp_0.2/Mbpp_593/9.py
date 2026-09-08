def removezero_ip(ip):
    """
    Remove leading zeroes from an IP address.
    
    Args:
    ip (str): The IP address from which leading zeroes need to be removed.
    
    Returns:
    str: The IP address with leading zeroes removed.
    """
    # Split the IP address into its components
    components = ip.split('.')
    
    # Remove leading zeroes from each component
    components = [component.lstrip('0') for component in components]
    
    # Join the components back into a single string
    return '.'.join(components)