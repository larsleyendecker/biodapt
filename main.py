import json
from pathlib import Path

from src.parameter_generator import generate_parameters, save_parameters_to_json


CONFIG_FILENAME = Path("./config/config.json")
DATA_FILENAME   = Path("./data/data.csv")
BATCH_SIZE      = 4
OUTPUT_FILENAME = "next_experiments.json"

def main() -> None:
    print("Starting Parameter Generation")
    trials = generate_parameters(
        config_filename=CONFIG_FILENAME,
        data_filename=DATA_FILENAME,
        batch_size=BATCH_SIZE,
    )

    save_parameters_to_json(
        data=trials,
        filename=OUTPUT_FILENAME
    )

    print("Suggested Parameter Sets:")
    print(json.dumps(trials, indent=4))


if __name__ == "__main__":
    main()