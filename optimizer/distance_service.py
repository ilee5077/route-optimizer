import requests


def compute_distance(from_node: dict, to_node: dict) -> dict:
    """Computes the distance and duration between two addresses."""

    orig_lat, orig_lon = from_node["latitude"], from_node["longitude"]
    dest_lat, dest_lon = to_node["latitude"], to_node["longitude"]
    osrm_url = f"http://localhost:5001/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=false"

    response = requests.get(osrm_url)
    data = response.json()

    if data.get("code") != "Ok":
        raise Exception(f"OSRM Error: {data.get('message', 'Failed to calculate route')}")

    route = data["routes"][0]
    
    return {
        "distance_km": round(route["distance"] / 1000.0, 2),
        "duration_mins": round(route["duration"] / 60.0, 1),
        "duration_secs": int(route["duration"])
    }

def compute_euclidean_distance(from_node: dict, to_node: dict) -> float:
    """Computes the Euclidean distance between two points."""
    from_x, from_y = from_node["x"], from_node["y"]
    to_x, to_y = to_node["x"], to_node["y"]

    # Simple Euclidean distance calculation (not accounting for Earth's curvature)
    return round(((from_x - to_x) ** 2 + (from_y - to_y) ** 2) ** 0.5, 2)

def compute_distance_matrix(data: dict) -> dict:
    """Computes a distance matrix between all locations using the compute_distance function."""
    # Each location is a dictionary that contains a name.
    # The matrix is stored as a nested 2d list.
    # Example: distances[0][3] = travel distance from depot to customer 3.
    locations = [data["depot"]] + data["customers"]
    distances = [[0 for _ in range(len(locations))] for _ in range(len(locations))]

    for from_counter, from_node in enumerate(locations):
        for to_counter, to_node in enumerate(locations):
            if from_counter == to_counter:
                # Distance from a node to itself is zero.
                distances[from_counter][to_counter] = 0
            else:
                if data['name'] == 'C101':
                    # For Solomon dataset, use Euclidean distance for simplicity.
                    distances[from_counter][to_counter] = compute_euclidean_distance(from_node, to_node)
                else:
                    # We assume one distance unit represents one minute of travel time.
                    # This is a simplified approximation for a demo routing model.
                    distances[from_counter][to_counter] = compute_distance(from_node, to_node)['duration_mins']

    data["distance_matrix"] = distances
    return data