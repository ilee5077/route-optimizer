from dataclasses import dataclass


@dataclass
class Location:
    """A depot or customer stop in a routing problem."""

    id: str | int
    demand: int
    ready_time: int
    due_time: int
    service_time: int
    address: str | None = None
    x: float | None = None #longitude
    y: float | None = None #latitude


@dataclass
class FleetSettings:
    """Vehicle count and shared capacity constraints."""

    vehicle_count: int
    vehicle_capacity: int 


@dataclass
class RoutingProblem:
    """Normalized input consumed by the route solver."""
    locations: list[Location]
    depot: Location
    customers: list[Location]
    fleet: FleetSettings
    distance_matrix: list[list[int]]
    duration_matrix: list[list[int]]
    demands: list[int]
    time_windows: list[tuple[int, int]]
    name: str | None = None

@dataclass
class SolverConfig:
    """Optional configuration parameters for the solver."""
    time_limit_seconds: int = 30  # Default time limit for the solver in seconds

class InputMode:
    """Enumeration for supported input modes."""
    SOLOMON = "solomon"
    GOOGLE = "google"
    LOCAL = "local"