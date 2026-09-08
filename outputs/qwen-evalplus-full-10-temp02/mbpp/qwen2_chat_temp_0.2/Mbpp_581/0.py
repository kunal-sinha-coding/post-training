# Define the function to calculate the surface area of a square pyramid
def surface_Area(base_edge, height):
    # Calculate the surface area using the formula: 2 * (base_edge * height) + 2 * (base_edge * base_edge)
    surface_area = 2 * (base_edge * height) + 2 * (base_edge * base_edge)
    return surface_area
