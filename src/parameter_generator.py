"""Bayesian optimization using Ax (Adaptive Experimentation) platform.

This script performs parameter optimization using historical data to suggest new
experimental configurations likely to improve specified objectives.
"""

import re
from typing import Dict, List, Any
from pathlib import Path
import json
import pandas as pd
import logging
import warnings
from ax import Arm
from ax.modelbridge.registry import Models
from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.service.ax_client import AxClient, ObjectiveProperties


def generate_parameters(config_filename: str, data_filename: str, batch_size: int) -> List[Dict[str, Any]]:
    """Generate optimized parameters using Bayesian optimization via Ax.

    Args:
        config_filename: Path to JSON config file containing objectives/parameters.
        data_filename: Path to CSV file containing historical experimental data.
        batch_size: Number of new parameter combinations to generate.

    Returns:
        List of dictionaries where each dictionary contains suggested parameters
        for a new trial, with keys as parameter names and values as values.
    """
    def sanitize(name: str) -> str:
        """Convert strings to snake_case by replacing spaces with underscores.

        Args:
            name: String to sanitize.

        Returns:
            Sanitized string with no leading/trailing spaces and single underscores.
        """
        return re.sub(r"\s+", "_", name.strip())

    def unsanitize(name: str) -> str:
        """Convert snake_case strings back to human-readable format.

        Args:
            name: String to unsanitize.

        Returns:
            String with underscores replaced by single spaces.
        """
        name = name.replace("_", " ")
        return re.sub(r"\s{2,}", " ", name).strip()

    def dict_of_dicts_to_trials(d: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert nested parameter dictionary into list of trial parameters.

        Args:
            d: Dictionary where keys are trial indices and values are parameter dicts.

        Returns:
            List of parameter dictionaries with unsanitized keys.
        """
        trials = []
        for _, param_dict in d.items():
            trial = {unsanitize(k): v for k, v in param_dict.items()}
            trials.append(trial)
        return trials

    # Suppress verbose logging from optimization libraries
    for name in logging.root.manager.loggerDict.keys():
        if name.startswith(("ax", "botorch", "gpytorch")):
            log = logging.getLogger(name)
            log.setLevel(logging.CRITICAL)
            log.propagate = False
            log.handlers.clear()

    # Ignore future warnings from Ax/pandas
    warnings.filterwarnings(
        "ignore", category=FutureWarning, module=r"(ax|pandas)\..*"
    )

    # Load configuration file
    with config_filename.open() as f:
        cfg_raw = json.load(f)

    # Extract and sanitize objective names from config
    objectives = [
        sanitize(cfg_raw["objective"]["name"]),
        sanitize(cfg_raw["objective"]["name2"]),
    ]

    # Prepare parameter ranges from config
    params = [
        {
            "name": sanitize(p["name"]),
            "type": "range",
            "bounds": [float(p["min"]), float(p["max"])],
        }
        for p in cfg_raw["parameters"]
    ]

    # Load and preprocess historical data
    data = pd.read_csv(data_filename)
    data = data.rename(columns=lambda c: sanitize(c))

    # Separate features (X) and objectives (Y)
    y = data[objectives]
    x = data[[p["name"] for p in params]]

    # Configure Bayesian optimization strategy
    # 
    gs = GenerationStrategy(
        name="botorch",
        steps=[
            GenerationStep(
                model=Models.BOTORCH_MODULAR, 
                num_trials=-1
            ),
        ],
    )

    # Initialize Ax client
    client = AxClient(generation_strategy=gs, verbose_logging=False)
    client.create_experiment(
        name="some_experiment_name",
        parameters=params,
        objectives={
            objectives[0]: ObjectiveProperties(minimize=False),
            objectives[1]: ObjectiveProperties(minimize=False),
        },
    )

    # Load historical data as completed trials
    for idx, row in x.iterrows():
        trial = client.experiment.new_trial()
        trial.add_arm(Arm(parameters=row.to_dict()))
        trial.mark_running(no_runner_required=True)
        client.complete_trial(
            trial_index=trial.index,
            raw_data={objectives[0]: y.iloc[idx, 0], objectives[1]: y.iloc[idx, 1]},
        )

    # Generate new parameter suggestions
    parameters, _ = client.get_next_trials(max_trials=batch_size)

    return dict_of_dicts_to_trials(parameters)

def save_parameters_to_json(data, filename):
    """Save parameters to JSON file in outputs folder.
    
    Args:
        data: List of parameter dictionaries
        filename: Output filename (default: parameters.json)
        
    Returns:
        Path to saved file
    """
    output_dir = Path("outputs")
    try:
        # Create outputs directory if it doesn't exist
        output_dir.mkdir(exist_ok=True)
        
        # Construct full file path
        filepath = output_dir / filename
        
        # Write JSON with pretty formatting
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        
        print(f"Successfully saved parameters to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Error saving parameters: {str(e)}")
        raise