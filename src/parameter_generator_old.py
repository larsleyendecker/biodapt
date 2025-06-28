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


def generate_parameters(CONFIG_FILENAME:str, DATA_FILENAME: str, BATCH_SIZE: int):
    def sanitize(name: str) -> str:
        return re.sub(r"\s+", "_", name.strip())


    def unsanitize(name: str) -> str:
        name = name.replace("_", " ")
        return re.sub(r"\s{2,}", " ", name).strip()

    def dict_of_dicts_to_trials(
            d: Dict[int, Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
            trials = []
            for _, param_dict in d.items():
                trial = {unsanitize(k): v for k, v in param_dict.items()}
                trials.append(trial)
            return trials

    for name in logging.root.manager.loggerDict.keys():
        if name.startswith(("ax", "botorch", "gpytorch")):
            log = logging.getLogger(name)
            log.setLevel(logging.CRITICAL)
            log.propagate = False
            log.handlers.clear()   
    warnings.filterwarnings(
        "ignore", category=FutureWarning, module=r"(ax|pandas)\..*"
    )
    
    with CONFIG_FILENAME.open() as f:
        cfg_raw = json.load(f)

    OBJECTIVES = [
        sanitize(cfg_raw["objective"]["name"]),
        sanitize(cfg_raw["objective"]["name2"]),
    ]
    PARAMS = [
        {
            "name": sanitize(p["name"]),
            "type": "range",
            "bounds": [float(p["min"]), float(p["max"])],
        }
        for p in cfg_raw["parameters"]
    ]
    
    data = pd.read_csv(DATA_FILENAME)
    data = data.rename(columns=lambda c: sanitize(c)) 

    Y = data[OBJECTIVES]
    X = data[[p["name"] for p in PARAMS]]  

    gs = GenerationStrategy(
        name="botorch",
        steps=[GenerationStep(model=Models.BOTORCH_MODULAR, num_trials=-1)],
    )
    client = AxClient(generation_strategy=gs, verbose_logging=False)
    client.create_experiment(
        name="some_experiment_name",
        parameters=PARAMS,
        objectives={
            OBJECTIVES[0]: ObjectiveProperties(minimize=False),
            OBJECTIVES[1]: ObjectiveProperties(minimize=False),
        },
    )

    for idx, row in X.iterrows():
        trial = client.experiment.new_trial()
        trial.add_arm(Arm(parameters=row.to_dict()))

        trial.mark_running(no_runner_required=True)
        client.complete_trial(
            trial_index=trial.index,
            raw_data={OBJECTIVES[0]: Y.iloc[idx, 0], OBJECTIVES[1]: Y.iloc[idx, 1]},
        )
    parameters, trialindex=client.get_next_trials(max_trials=BATCH_SIZE)

    return dict_of_dicts_to_trials(parameters)