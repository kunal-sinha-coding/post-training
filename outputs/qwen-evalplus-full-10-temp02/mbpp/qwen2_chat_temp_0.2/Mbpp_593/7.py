def removezero_ip(ip):
    # Split the IP address into its components
    components = ip.split('.')
    # Remove leading zeros from each component
    components = [component.lstrip('0') for component in components]
    # Join the components back into a single string
    return '.'.join(components)