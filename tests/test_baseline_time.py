import torch
import numpy as np
from src.eval import load_original_model_and_inputs, time_execution_with_cuda_event, get_timing_stats, set_seed, fetch_ref_arch_from_problem_id
from src.utils import construct_problem_dataset_from_problem_dir
import os
import json

device = torch.device("cuda:0")

REPO_TOP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',))
KERNEL_BENCH_PATH = os.path.join(REPO_TOP_PATH, "KernelBench")

json_results = {}

def fetch_ref_arch_from_level_problem_id(level_num, problem_id, with_name=False):
    PROBLEM_DIR = os.path.join(KERNEL_BENCH_PATH, 'level'+str(level_num))
    dataset = construct_problem_dataset_from_problem_dir(PROBLEM_DIR)
    return fetch_ref_arch_from_problem_id(problem_id, dataset, with_name)

def get_time(level_num, problem_id, num_trials=100, torch_compile=False):
    ref_arch_name, ref_arch_src = fetch_ref_arch_from_level_problem_id(level_num, problem_id, with_name=True)
    context = {}
    Model, get_init_inputs, get_inputs = load_original_model_and_inputs(ref_arch_src, context)
    try: 
        torch.cuda.synchronize(device=device)
        set_seed(42)
        inputs = get_inputs()
        set_seed(42)
        init_inputs = get_init_inputs()
        inputs = [x.cuda(device=device) if isinstance(x, torch.Tensor) else x for x in inputs]
        init_inputs = [x.cuda(device=device) if isinstance(x, torch.Tensor) else x for x in init_inputs]
        model = Model(*init_inputs)
        if torch_compile:
            model = torch.compile(model)
        model = model.cuda(device=device)
        torch.cuda.synchronize(device=device)
        elapsed_times = time_execution_with_cuda_event(model, *inputs, num_trials=num_trials, verbose=False, device=device)
        runtime_stats = get_timing_stats(elapsed_times, device=device)
        json_results[f"level{level_num}"][ref_arch_name] = runtime_stats
    except Exception as e:
        print(f"[Eval] Error in Measuring Performance: {e}")

if __name__ == "__main__":

    REPO_TOP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',))
    KERNEL_BENCH_PATH = os.path.join(REPO_TOP_PATH, "KernelBench")

    torch_compile = True

    PROBLEM_DIR_LEVEL1 = "KernelBench/level1"
    dataset_level1 = construct_problem_dataset_from_problem_dir(PROBLEM_DIR_LEVEL1)
    json_results["level1"] = {}
    for problem_id in range(len(dataset_level1)):
        get_time(1, problem_id, torch_compile=torch_compile)

    PROBLEM_DIR_LEVEL2 = "KernelBench/level2"
    dataset_level2 = construct_problem_dataset_from_problem_dir(PROBLEM_DIR_LEVEL2)
    json_results["level2"] = {}
    for problem_id in range(len(dataset_level2)):
        get_time(2, problem_id, torch_compile=torch_compile)

    PROBLEM_DIR_LEVEL3 = "KernelBench/level3"
    dataset_level3 = construct_problem_dataset_from_problem_dir(PROBLEM_DIR_LEVEL3)
    json_results["level3"] = {}
    for problem_id in range(len(dataset_level3)):
        get_time(3, problem_id, torch_compile=torch_compile)

    if torch_compile:
        save_path = f"tests/baseline_time_torch_compile.json"
    else:
        save_path = f"tests/baseline_time.json"
    with open(save_path, "w") as f:
        json.dump(json_results, f)

