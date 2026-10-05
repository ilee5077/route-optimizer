from optimizer.data_loader import build_routing_problem
from optimizer.solver import solve_vrptw


def main():
    problem = build_routing_problem(
        "data/jb_hifi_nsw.csv",
        mode="google",
        fleet_config={"total_vehicles": 5, "vehicle_capacity": 200},
    )
    result = solve_vrptw(problem)


if __name__ == "__main__":
    main()
