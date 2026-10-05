import pandas as pd
from pathlib import Path

from optimizer.distance_service import build_distance_matrix
from optimizer.model import FleetSettings, InputMode, Location, RoutingProblem


def load_input_data(file_path: str) -> dict:
    """Loads CSV customer data and normalizes it into the format expected by the solver."""
    if file_path.endswith('.csv'):
        # Read the CSV using pandas so the depot and customer rows can be interpreted cleanly.
        df = pd.read_csv(file_path)

        # add all rows to a list of Location objects, starting with the depot (first row) and then the customers (subsequent rows)
        locations = []

        for i, loc in df.iterrows():
            locations.append(Location(
                id=i,
                address=loc.Address,
                demand=int(loc.Demand),
                ready_time=int(loc.ReadyTime),
                due_time=int(loc.DueDate),
                service_time=int(loc.ServiceTime),
                x=None,
                y=None,
            ))

        # The CSV format appears to place the depot as the first row and the customers afterward.
        # We convert that into a RoutingProblem object with a depot and a list of customers.
        return RoutingProblem(
            name=Path(file_path).stem,
            depot=locations[0],
            customers=locations[1:],
            locations=locations,
            fleet=FleetSettings(vehicle_count=0, vehicle_capacity=0),  # Placeholder; will be set later if needed
            distance_matrix=[[0] * len(locations) for _ in locations],
            duration_matrix=[[0] * len(locations) for _ in locations],
            demands=[loc.demand for loc in locations],
            time_windows=[(loc.ready_time, loc.due_time) for loc in locations],
        )
    else:
        # Fail early with a clear message if an unsupported file type is passed in.
        raise ValueError("Unsupported file format. Use CSV.")

def parse_solomon_text(raw_data: str) -> tuple[dict, FleetSettings]:
    """Parse a Solomon VRPTW instance and return its fleet settings separately."""
    lines = [line.strip() for line in raw_data.splitlines()]

    vehicle_header = lines.index("VEHICLE")
    vehicle_values = lines[vehicle_header + 2].split()
    num_vehicles, vehicle_capacity = map(int, vehicle_values[:2])

    customer_header = lines.index("CUSTOMER")
    locations = []
    for line in lines[customer_header + 2:]:
        fields = line.split()
        if len(fields) < 7:
            continue
        customer_id, x_coord, y_coord, demand, ready_time, due_date, service_time = map(
            int, fields[:7]
        )
        locations.append(
            Location(
                id=customer_id,
                address=None,
                demand=demand,
                ready_time=ready_time,
                due_time=due_date,
                service_time=service_time,
                x=x_coord,
                y=y_coord,
            )
        )

    if not locations or locations[0].id != 0:
        raise ValueError("Solomon data must start with depot customer 0")

    problem_data = {
        "name": lines[0],
        "distance_metric": "euclidean",
        "depot": locations[0],
        "customers": locations[1:],
    }

    return RoutingProblem(
        locations=locations,
        depot=locations[0],
        customers=locations[1:],
        fleet=FleetSettings(vehicle_count=num_vehicles, vehicle_capacity=vehicle_capacity),
        distance_matrix=[[0] * len(locations) for _ in locations],
        duration_matrix=[[0] * len(locations) for _ in locations],
        demands=[loc.demand for loc in locations],
        time_windows=[(loc.ready_time, loc.due_time) for loc in locations],
        name=lines[0],
    )


def load_solomon_file(file_path: str) -> tuple[dict, FleetSettings]:
    """Read and parse a Solomon instance file and its fleet settings."""
    raw_data = Path(file_path).read_text(encoding="utf-8")
    return parse_solomon_text(raw_data)

def prepare_solver_data(problem: RoutingProblem) -> RoutingProblem:
    """Defines the constraints for the VRPTW problem."""

    data['nodes'] = [problem.depot] + problem.customers # need this
    data['demands'] = [0] * len(data['nodes']) # need this
    data['time_windows'] = [(0, 0)] * len(data['nodes']) # need this


    # construct demand and time window constraints for each node
    data['demands'][data["depot"].id] = 0  # depot has no demand
    data['time_windows'][data["depot"].id] = (
        data["depot"].ready_time,
        data["depot"].due_time,
    )

    for customer in data["customers"]:
        data['demands'][customer.id] = customer.demand
        data['time_windows'][customer.id] = (customer.ready_time, customer.due_time)

    return RoutingProblem(
        depot=data["depot"],
        customers=data["customers"],
        fleet=FleetSettings(
            vehicle_count=data["fleet_config"]["total_vehicles"],
            vehicle_capacity=data["fleet_config"]["vehicle_capacity"],
        ),
        distance_matrix=data['distance_matrix'],
        duration_matrix=data['duration_matrix'],
        name=data.get("name"),
    )

def build_routing_problem(
    path: str,
    mode: InputMode,
    fleet_config: FleetSettings | None = None
) -> RoutingProblem:
    """Loads and prepares a routing problem from a file path."""
    if mode == InputMode.SOLOMON:
        problem = load_solomon_file(path)
        problem = build_distance_matrix(problem, mode)
    elif mode == InputMode.GOOGLE:
        problem = load_input_data(path)
        problem = build_distance_matrix(problem, mode)
    elif mode == InputMode.LOCAL:
        raw_data = load_input_data(path)
        problem = prepare_solver_data(raw_data, fleet_config=fleet_config)
    else:
        raise ValueError(f"Unsupported input mode: {mode}")

    return problem

