import os
from pathlib import Path
from time import time

import requests
from dotenv import load_dotenv

from optimizer.model import Location, RoutingProblem, InputMode


def compute_distance(from_node: dict, to_node: dict) -> dict:
    """Computes the distance and duration between two addresses."""

    orig_lat, orig_lon = from_node["latitude"], from_node["longitude"]
    dest_lat, dest_lon = to_node["latitude"], to_node["longitude"]
    osrm_url = f"http://localhost:5001/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=false"

    response = requests.get(osrm_url, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("code") != "Ok":
        raise Exception(f"OSRM Error: {data.get('message', 'Failed to calculate route')}")

    route = data["routes"][0]
    
    return {
        "distance_km": round(route["distance"] / 1000.0, 2),
        "duration_mins": round(route["duration"] / 60.0, 1),
        "duration_secs": int(route["duration"])
    }


def compute_google_maps_route(from_node: dict, to_node: dict) -> dict:
    """Compute driving distance and duration using the Google Maps Distance Matrix API."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    api_key = os.getenv("GOOGLE_MAPS_DEMO_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_MAPS_DEMO_API_KEY is not set in the environment or project .env file."
        )

    response = requests.post(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.routeToken,routes.travelAdvisory.routeRestrictionsPartiallyIgnored",
        },
        json={
            "origin": {
                "address": from_node.address,
            },
            "destination": {
                "address": to_node.address,
            },
            "travelMode": "TRUCK",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        },
    )
    
    response.raise_for_status()
    data = response.json()

    distance_meters = data["routes"][0]["distanceMeters"]
    duration_seconds = data["routes"][0]["duration"][:-1]  # truncate the s at the end of the string and convert to int
    return {
        "distance_m": int(distance_meters),
        "duration_s": int(float(duration_seconds))
    }

def compute_euclidean_distance(from_node: Location, to_node: Location) -> float:
    """Computes the Euclidean distance between two points."""
    from_x, from_y = from_node.x, from_node.y
    to_x, to_y = to_node.x, to_node.y

    # Simple Euclidean distance calculation (not accounting for Earth's curvature)
    return round(((from_x - to_x) ** 2 + (from_y - to_y) ** 2) ** 0.5)

def compute_distance_matrix(problem: RoutingProblem, method: InputMode) -> RoutingProblem:
    """Computes a distance matrix between all locations using the compute_distance function."""
    # Each location is a dictionary that contains a name.
    # The matrix is stored as a nested 2d list.
    # Example: distances[0][3] = travel distance from depot to customer 3.
    locations = [problem.depot] + problem.customers

    if method != InputMode.GOOGLE:
        for from_counter, from_node in enumerate(locations):
            for to_counter, to_node in enumerate(locations):
                if from_counter == to_counter:
                    # Distance from a node to itself is zero.
                    problem.distance_matrix[from_counter][to_counter] = 0
                else:
                    if method == InputMode.SOLOMON:
                        # Solomon benchmark coordinates use Euclidean distance.
                        problem.distance_matrix[from_counter][to_counter] = compute_euclidean_distance(from_node, to_node)
                    else:
                        # We assume one distance unit represents one minute of travel time.
                        # This is a simplified approximation for a demo routing model.
                        problem.distance_matrix[from_counter][to_counter] = compute_distance(from_node, to_node)['duration_mins']
    elif method == InputMode.GOOGLE:
        for from_counter, from_node in enumerate(locations):
            for to_counter, to_node in enumerate(locations):
                if from_counter == to_counter:
                    problem.distance_matrix[from_counter][to_counter] = 0
                    problem.duration_matrix[from_counter][to_counter] = 0
                else:
                    result = compute_google_maps_route(from_node, to_node)
                    time.sleep(0.1)  # Add a small delay to avoid hitting API rate limits
                    problem.duration_matrix[from_counter][to_counter] = result['duration_s']
                    problem.distance_matrix[from_counter][to_counter] = result['distance_m']

    return problem


def build_distance_matrix(problem: RoutingProblem, mode: InputMode) -> RoutingProblem:
    """Builds a distance matrix for the routing problem based on the specified mode."""
    if mode == InputMode.LOCAL:
        #fill coordinates for local mode
        1==1
    elif mode == InputMode.SOLOMON:
        problem = compute_distance_matrix(problem, method="euclidean")
    elif mode == InputMode.GOOGLE:
        problem = compute_distance_matrix(problem, method="google")

    return problem