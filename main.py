import json
from pathlib import Path

from parameter_generator_old import generate_parameters


CONFIG_FILENAME = Path("./config/config.json")
DATA_FILENAME   = Path("./data/data.csv")
BATCH_SIZE      = 4

def main() -> None:
    print("Starting Parameter Generation")
    trials = generate_parameters(
        CONFIG_FILENAME=CONFIG_FILENAME,
        DATA_FILENAME=DATA_FILENAME,
        BATCH_SIZE=BATCH_SIZE,
    )
    print("Suggested Parameter Sets:")
    print(json.dumps(trials, indent=4))


if __name__ == "__main__":
    main()