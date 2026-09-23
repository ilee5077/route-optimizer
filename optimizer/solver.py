import json
from fastapi import routing
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from optimizer.data_loader import load_input_data, load_solomon_file
from optimizer.geocoder import geocode_address
from optimizer.distance_service import compute_distance_matrix



def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f"Objective: {solution.ObjectiveValue()}")
    time_dimension = routing.GetDimensionOrDie("Time")
    total_time = 0
    total_distance = 0
    total_vehicles_used = 0
    for vehicle_id in range(data["num_vehicles"]):
        if not routing.IsVehicleUsed(solution, vehicle_id):
            continue
        total_vehicles_used += 1
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            plan_output += (
                f"{manager.IndexToNode(index)}"
                f" Time({solution.Min(time_var)},{solution.Max(time_var)})"
                " -> "
            )
            if routing.IsEnd(solution.Value(routing.NextVar(index))): #back to depot
                total_distance += data['distance_matrix'][manager.IndexToNode(index)][manager.IndexToNode(routing.Start(vehicle_id))]
            else:
                total_distance += data['distance_matrix'][manager.IndexToNode(index)][solution.Value(routing.NextVar(index))]
            index = solution.Value(routing.NextVar(index))
        time_var = time_dimension.CumulVar(index)
        plan_output += (
            f"{manager.IndexToNode(index)}"
            f" Time({solution.Min(time_var)},{solution.Max(time_var)})\n"
        )
        plan_output += f"Time of the route: {solution.Min(time_var)}min\n"
        print(plan_output)
        total_time += solution.Min(time_var)
    print(f"Total time of all routes: {total_time}min")
    print(f"Total distance of all routes: {total_distance}km")
    print(f"Total vehicles used: {total_vehicles_used}")

def define_constraints(data: dict) -> dict:
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

def solve_vrptw(data_path: str) -> dict:
    """Main solver pipeline using Google OR-Tools to optimize vehicle routes under capacity and time-window constraints."""

    data = load_solomon_file(data_path)

    data = compute_distance_matrix(data)

    data = define_constraints(data)
    
    # OR-Tools requires an index manager that maps between internal routing indices and real node IDs.
    # The manager handles the translation between node positions like 0, 1, 2... and the model's indices.
    manager = pywrapcp.RoutingIndexManager(len(data["distance_matrix"]), data["num_vehicles"], data["depot"]["id"])
    routing = pywrapcp.RoutingModel(manager)


    # Capacity constraints are added as a dimension.
    # This prevents a single vehicle from exceeding the assigned capacity limit while traversing stops.
    def demand_callback(from_index):
        # Look up the node represented by the routing index.
        from_node = manager.IndexToNode(from_index)
        # Each node may have a demand value; if absent, assume zero demand.
        return data["demands"][from_node]

    # This binary callback measures the demand attached to each node.
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    # AddVehicleCapacity enforces that each vehicle's cumulative load stays within its capacity limit.
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack: no extra room beyond the cap is allowed
        [data['vehicle_capacity']] * data['num_vehicles'],
        True,  # start at zero for each vehicle's cumulative load
        'Capacity'
    )

    # Time window constraints are modeled as a time dimension.
    # The dimension tracks cumulative time as each vehicle travels between stops and serves customers.
    def time_callback(from_index, to_index):
        # Convert the routing index back to logical locations.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # Service time is added when a vehicle leaves the current stop to the next stop.
        service_time = data['nodes'][from_node]['service_time']
        return int(round(data["distance_matrix"][from_node][to_node] + service_time))

    # Register the callback and attach a time dimension to the route planning model.
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    routing.AddDimension(
        transit_callback_index,
        99999,   # allow waiting time
        data["depot"]['due_date'],  # maximum time per vehicle
        False,  # do not force the start time to be zero for the route
        'Time'
    )
    time_dimension = routing.GetDimensionOrDie('Time')

    # Apply time-window restrictions to each stop.
    # For every node, the cumulative time variable must remain within a permissible range.
    # run through data['time_windows'] list one by one with index
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == data["depot"]["id"]:
            continue  # Skip the depot; its time window is already handled.
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    depot_idx = data["depot"]["id"]
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            data["time_windows"][depot_idx][0], data["time_windows"][depot_idx][1]
        )

    # Instantiate route start and end times to produce feasible times.
    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    # Search parameters control how the solver explores the problem space.
    # The chosen strategy is a faster greedy method that tends to produce a feasible first route quickly.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 5  # Keep the calculation lightweight for a demo or pitch workflow.

    # Solve the optimization model with the configured search strategy.
    solution = routing.SolveWithParameters(search_parameters)

    # If no valid solution is found, return a structured failure payload instead of crashing.
    if not solution:
        return {"success": False, "error": "No feasible route found within constraints."}
    else:
        print_solution(data, manager, routing, solution)


    # Return a structured output that can be consumed by a dashboard, API, or audit report.
    return {
        "success": True
    }
