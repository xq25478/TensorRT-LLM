import subprocess
from typing import List, Optional

import pytest
import torch

from tensorrt_llm import LLM, BuildConfig, SamplingParams
from tensorrt_llm.hlapi import QuantAlgo, QuantConfig
from tensorrt_llm.hlapi.utils import get_total_gpu_memory

try:
    from .test_llm import get_model_path
except ImportError:
    from test_llm import get_model_path

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.util import force_ampere, similar, skip_pre_ampere, skip_pre_hopper

gptj_model_path = get_model_path('gpt-j-6b')
gpt2_model_path = get_model_path('gpt2-medium')
starcoder2_model_path = get_model_path('starcoder2-3b')
phi_1_5_model_path = get_model_path('phi-1_5')
phi_2_model_path = get_model_path('phi-2')
phi_3_mini_4k_model_path = get_model_path('Phi-3/Phi-3-mini-4k-instruct')
phi_3_small_8k_model_path = get_model_path('Phi-3/Phi-3-small-8k-instruct')
phi_3_medium_4k_model_path = get_model_path('Phi-3/Phi-3-medium-4k-instruct')
falcon_model_path = get_model_path('falcon-rw-1b')
gemma_2b_model_path = get_model_path('gemma/gemma-2b')
gemma_2_9b_it_model_path = get_model_path('gemma/gemma-2-9b-it')
glm_model_path = get_model_path('chatglm3-6b')
baichuan_7b_model_path = get_model_path('Baichuan-7B')
baichuan_13b_model_path = get_model_path('Baichuan-13B-Chat')
baichuan2_7b_model_path = get_model_path('Baichuan2-7B-Chat')
baichuan2_13b_model_path = get_model_path('Baichuan2-13B-Chat')
qwen_model_path = get_model_path('Qwen-1_8B-Chat')
qwen1_5_model_path = get_model_path('Qwen1.5-0.5B-Chat')
qwen2_model_path = get_model_path('Qwen2-7B-Instruct')

sampling_params = SamplingParams(max_tokens=10)


def skip_less_than_memory(required_memory: int):
    memory = get_total_gpu_memory(0)
    return pytest.mark.skipif(
        required_memory > memory,
        reason=
        f'Not enough GPU memory for this test (wanted {required_memory}, have {memory})'
    )


skip_less_than_40gb_memory = skip_less_than_memory(40 * 1024 * 1024 * 1024)


def llm_test_harness(model_dir: str,
                     prompts: List[str],
                     references: List[str],
                     *,
                     sampling_params: Optional[SamplingParams] = None,
                     similar_threshold: float = 0.8,
                     **llm_kwargs):

    # skip if no enough GPUs
    tp_size = llm_kwargs.get('tensor_parallel_size', 1)
    pp_size = llm_kwargs.get('pipeline_parallel_size', 1)
    world_size = tp_size * pp_size
    if world_size > torch.cuda.device_count():
        pytest.skip(
            f"world_size ({world_size}) is greater than available GPUs ({torch.cuda.device_count()})"
        )

    llm = LLM(model_dir, tokenizer=model_dir, **llm_kwargs)
    outputs = llm.generate(prompts, sampling_params=sampling_params)
    print(outputs)
    for out, ref in zip(outputs, references):
        assert similar(out.outputs[0].text, ref, threshold=similar_threshold)


@force_ampere
def test_llm_gptj():
    llm_test_harness(gptj_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_gptj_int4_weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W4A16)
    llm_test_harness(gptj_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@force_ampere
def test_llm_gpt2():
    llm_test_harness(gpt2_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_gpt2_sq():
    quant_config = QuantConfig(
        quant_algo=QuantAlgo.W8A8_SQ_PER_CHANNEL_PER_TOKEN_PLUGIN,
        kv_cache_quant_algo=QuantAlgo.INT8)
    llm_test_harness(gpt2_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@force_ampere
def test_llm_gpt2_int8_weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W8A16,
                               kv_cache_quant_algo=QuantAlgo.INT8)
    llm_test_harness(gpt2_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@skip_pre_hopper
def test_llm_gpt2_fp8():
    quant_config = QuantConfig(quant_algo=QuantAlgo.FP8)
    llm_test_harness(gpt2_model_path,
                     prompts=["A B C"],
                     references=["D E F G H I J K L M"],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@force_ampere
def test_llm_starcoder2():
    llm_test_harness(starcoder2_model_path,
                     prompts=["def print_hello_world():"],
                     references=['\n    print("Hello World")\n\ndef print'],
                     sampling_params=sampling_params)


@skip_pre_hopper
def test_llm_starcoder2_fp8():
    quant_config = QuantConfig(quant_algo=QuantAlgo.FP8)
    llm_test_harness(starcoder2_model_path,
                     prompts=["def print_hello_world():"],
                     references=['\n    print("Hello World")\n\ndef print'],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


def test_llm_phi_1_5():
    llm_test_harness(phi_1_5_model_path,
                     prompts=['A B C'],
                     references=[' D E F G H I J K L M'],
                     sampling_params=sampling_params)


def test_llm_phi_2():
    llm_test_harness(phi_2_model_path,
                     prompts=['A B C'],
                     references=[' D E F G H I J K L M'],
                     sampling_params=sampling_params)


def test_llm_phi_3_mini_4k():
    phi_requirement_path = os.path.join(os.getenv("LLM_ROOT"),
                                        "examples/phi/requirements.txt")
    command = f"pip install -r {phi_requirement_path}"
    subprocess.run(command, shell=True, check=True, env=os.environ)
    phi3_mini_4k_sampling_params = SamplingParams(max_tokens=13)

    llm_test_harness(
        phi_3_mini_4k_model_path,
        prompts=["I am going to Paris, what should I see?"],
        references=["\n\nAssistant: Paris is a city rich in history,"],
        sampling_params=phi3_mini_4k_sampling_params)


@force_ampere
def test_llm_phi_3_small_8k():
    phi_requirement_path = os.path.join(os.getenv("LLM_ROOT"),
                                        "examples/phi/requirements.txt")
    command = f"pip install -r {phi_requirement_path}"
    subprocess.run(command, shell=True, check=True, env=os.environ)
    build_config = BuildConfig()
    build_config.plugin_config._gemm_plugin = 'auto'
    llm_test_harness(
        phi_3_small_8k_model_path,
        prompts=["where is France's capital?"],
        references=[' Paris is the capital of France. It is known'],
        sampling_params=sampling_params,
        build_config=build_config)


@force_ampere
def test_llm_falcon():
    llm_test_harness(falcon_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_falcon_int4_weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W4A16)
    llm_test_harness(falcon_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params,
                     quant_config=quant_config,
                     build_config=BuildConfig(strongly_typed=False))


@force_ampere
def test_llm_gemma_2b():
    llm_test_harness(gemma_2b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@pytest.mark.skip(reason="https://nvbugspro.nvidia.com/bug/4575937")
def test_llm_gemma_2b_int4weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W4A16)
    llm_test_harness(gemma_2b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@force_ampere
def test_llm_gemma_2_9b_it():
    llm_test_harness(gemma_2_9b_it_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


def test_llm_glm():
    print('test GLM....')
    llm_test_harness(glm_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_baichuan_7b():
    llm_test_harness(baichuan_7b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_baichuan2_7b():
    llm_test_harness(baichuan2_7b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
@skip_less_than_40gb_memory
def test_llm_baichuan_13b():
    llm_test_harness(baichuan_13b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
@skip_less_than_40gb_memory
def test_llm_baichuan2_13b():
    llm_test_harness(baichuan2_13b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@force_ampere
def test_llm_baichuan2_7b_int4weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W4A16)
    llm_test_harness(baichuan2_7b_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@skip_pre_ampere
def test_llm_qwen():
    qwen_requirement_path = os.path.join(os.getenv("LLM_ROOT"),
                                         "examples/qwen/requirements.txt")
    command = f"pip install -r {qwen_requirement_path}"
    subprocess.run(command, shell=True, check=True, env=os.environ)
    llm_test_harness(qwen_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@skip_pre_ampere
def test_llm_qwen1_5():
    qwen1_5_sampling_params = SamplingParams(max_tokens=10)
    llm_test_harness(qwen1_5_model_path,
                     prompts=['1+1='],
                     references=['2'],
                     sampling_params=qwen1_5_sampling_params)


@skip_pre_ampere
def test_llm_qwen2():
    llm_test_harness(qwen2_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params)


@skip_pre_ampere
def test_llm_qwen2_int4_weight_only():
    quant_config = QuantConfig(quant_algo=QuantAlgo.W4A16)
    llm_test_harness(qwen2_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


@skip_pre_hopper
def test_llm_qwen2_fp8():
    quant_config = QuantConfig(quant_algo=QuantAlgo.FP8)
    llm_test_harness(qwen2_model_path,
                     prompts=['A B C'],
                     references=['D E F G H I J K L M'],
                     sampling_params=sampling_params,
                     quant_config=quant_config)


if __name__ == '__main__':
    test_llm_gptj()
    test_llm_phi_1_5()
    test_llm_phi_2()
    test_llm_phi_3_mini_4k()
    test_llm_phi_3_small_8k()
    test_llm_glm()
