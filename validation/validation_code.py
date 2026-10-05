from optimizer.model import FleetSettings, RoutingProblem


def validate_vrptw_solution(problem: RoutingProblem, manager, routing, assignment):
    time_dimension = routing.GetDimensionOrDie("Time")
    capacity_dimension = routing.GetDimensionOrDie("Capacity")
    
    violations = []
    
    for vehicle_id in range(problem.fleet.vehicle_count):
        index = routing.Start(vehicle_id)
        
        # 1. Seed clock with depot start window
        depot_node = manager.IndexToNode(index)
        current_time = problem.time_windows[depot_node][0]
        current_load = 0
        
        while True:
            node = manager.IndexToNode(index)
            
            # Extract OR-Tools values
            time_var = time_dimension.CumulVar(index)
            cap_var = capacity_dimension.CumulVar(index)
            
            solver_time = assignment.Value(time_var)
            solver_load = assignment.Value(cap_var)
            
            # --- Check A: Capacity ---
            if current_load > problem.fleet.vehicle_capacity:
                violations.append(f"Vehicle {vehicle_id} capacity exceeded at node {node}. Load: {current_load}")
            if solver_load != current_load:
                violations.append(f"Vehicle {vehicle_id} load mismatch at node {node}. Solver: {solver_load}, Calc: {current_load}")
            current_load += problem.demands[node]

            # --- Check B: Hard Time Window ---
            ready_time, due_time = problem.time_windows[node]
            if solver_time < ready_time or solver_time > due_time:
                violations.append(f"Vehicle {vehicle_id} time window violated at node {node}. Solver time: {solver_time}, Window: [{ready_time}, {due_time}]")
                
            # --- Check C: Simulation Clock Alignment ---
            # Arrival time is either when we get there or when the node opens (waiting time)
            expected_arrival = max(current_time, ready_time)
            if solver_time != expected_arrival:
                violations.append(f"Vehicle {vehicle_id} timing drift at node {node}. Solver: {solver_time}, Calc: {expected_arrival}")

            # Stop loop after validating the return to depot (End node)
            if routing.IsEnd(index):
                break

            # --- Advance Clock to Next Hop ---
            next_index = assignment.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(next_index)

            travel_time = problem.distance_matrix[node][next_node]
            service_time = problem.locations[node].service_time
            
            # Departure time = start of service + service duration + travel time
            current_time = expected_arrival + service_time + travel_time
            
            index = next_index

    # --- Check D: Unvisited Nodes ---
    # The depot is part of all_nodes, but is intentionally skipped while
    # collecting customer visits. Count it as visited so it isn't reported
    # as unassigned.
    visited_nodes = {problem.depot.id}
    for vehicle_id in range(problem.fleet.vehicle_count):
        index = routing.Start(vehicle_id)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != problem.depot.id:
                visited_nodes.add(node)
            index = assignment.Value(routing.NextVar(index))
            
    all_nodes = set(range(len(problem.time_windows)))
    unvisited = all_nodes - visited_nodes
    if unvisited:
        violations.append(f"Unassigned nodes detected: {unvisited}")

    return len(violations) == 0, violations