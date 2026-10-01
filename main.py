import json

from optimizer.solver import solve_vrptw
from optimizer.output_writer import save_result


def main():
    result = solve_vrptw("data/Solomon/r206.txt")

if __name__ == "__main__":
    main()