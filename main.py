import json

from optimizer.data_loader import build_routing_problem, load_solomon_file, prepare_solver_data
from optimizer.distance_service import compute_distance_matrix
from optimizer.solver import solve_vrptw
from optimizer.output_writer import save_result


def main():
    problem = build_routing_problem("data/jb_hifi_nsw.csv", mode="google", fleet_config={"total_vehicles": 5, "vehicle_capacity": 200})
    result = solve_vrptw(problem)

if __name__ == "__main__":
    main()