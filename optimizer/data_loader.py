import pandas as pd
from pathlib import Path

def load_input_data(file_path: str) -> dict:
    """Loads CSV customer data and normalizes it into the format expected by the solver."""
    if file_path.endswith('.csv'):
        # Read the CSV using pandas so the depot and customer rows can be interpreted cleanly.
        df = pd.read_csv(file_path)

        # The CSV format appears to place the depot as the first row and the customers afterward.
        # We convert that into a consistent internal structure:
        # - fleet_config: vehicle count and capacity
        # - depot: the starting location for each route
        # - customers: all remaining stops to visit
        # This keeps the solver logic independent of the original source file type.
        return {
            "fleet_config": {"total_vehicles": 3, "vehicle_capacity": 100},
            "depot": {
                "id": 0,
                "name": df.iloc[0]['name'],
                "open_time": 0,
                "close_time": 480
            },
            "customers": df.iloc[1:].to_dict(orient='records')
        }
    else:
        # Fail early with a clear message if an unsupported file type is passed in.
        raise ValueError("Unsupported file format. Use CSV.")

def parse_solomon_text(raw_data: str) -> dict:
    """Parse a Solomon VRPTW instance from text."""
    lines = [line.strip() for line in raw_data.splitlines()]

    vehicle_header = lines.index("VEHICLE")
    vehicle_values = lines[vehicle_header + 2].split()
    num_vehicles, vehicle_capacity = map(int, vehicle_values[:2])

    customer_header = lines.index("CUSTOMER")
    customers = []
    for line in lines[customer_header + 2:]:
        fields = line.split()
        if len(fields) < 7:
            continue
        customer_id, x_coord, y_coord, demand, ready_time, due_date, service_time = map(
            int, fields[:7]
        )
        customers.append({
            "id": customer_id,
            "x": x_coord,
            "y": y_coord,
            "demand": demand,
            "ready_time": ready_time,
            "due_date": due_date,
            "service_time": service_time,
        })

    if not customers or customers[0]["id"] != 0:
        raise ValueError("Solomon data must start with depot customer 0")

    return {
        "name": lines[0],
            "distance_metric": "euclidean",
        "num_vehicles": num_vehicles,
        "vehicle_capacity": vehicle_capacity,
        "depot": customers[0],
        "customers": customers[1:],
    }


def load_solomon_file(file_path: str) -> dict:
    """Read and parse a Solomon instance file."""
    raw_data = Path(file_path).read_text(encoding="utf-8")
    return parse_solomon_text(raw_data)

def prepare_solver_data(data: dict) -> dict:
    """Defines the constraints for the VRPTW problem."""

    data['nodes'] = [data["depot"]] + data["customers"]
    data['demands'] = [0] * len(data['nodes'])
    data['time_windows'] = [(0, 0)] * len(data['nodes'])


    # construct demand and time window constraints for each node
    data['demands'][data["depot"]["id"]] = 0  # depot has no demand
    data['time_windows'][data["depot"]["id"]] = (data["depot"]["ready_time"], data["depot"]["due_date"])

    for idx, customer in enumerate(data["customers"]):
        data['demands'][customer["id"]] = customer["demand"]
        data['time_windows'][customer["id"]] = (customer["ready_time"], customer["due_date"])

    return data