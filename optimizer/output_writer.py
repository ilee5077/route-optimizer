import json
from datetime import datetime
from pathlib import Path


def save_result(result: dict, output_dir: str = "outputs", filename: str | None = None):
    Path(output_dir).mkdir(exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sydney_routes_{timestamp}.json"

    output_path = Path(output_dir) / filename
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    return str(output_path)
