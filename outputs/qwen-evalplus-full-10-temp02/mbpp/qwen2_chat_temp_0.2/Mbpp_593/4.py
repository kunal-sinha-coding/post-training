def removezero_ip(ip_address):
    # Split the IP address into its components
    components = ip_address.split('.')
    # Remove any leading zeros from the components
    components = [component for component in components if component != '0']
    # Join the components back into a string with a dot as the separator
    return '.'.join(components)