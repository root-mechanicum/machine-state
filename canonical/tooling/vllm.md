# vLLM

## Function

Local inference server for the Qwen3.8-27B multimodal model. It is an application-layer
experiment, not a substrate dependency; the model weights and Python environment live in the
user's home directory and are not projected by `machine-state`.

## Intended setup

Use an isolated Python 3.13 environment, installed with `uv`, and serve
`RedHatAI/Qwen3.8-27B-INT4` through vLLM's OpenAI-compatible server. The vLLM recipe lists this
compressed-tensors W4A16 checkpoint at about 19.5 GB with a 24 GB minimum and RTX 5090 support.
That leaves materially more room than either NVFP4 candidate for the vision tower, runtime
buffers, and KV cache. The NVIDIA mixed NVFP4/FP8 checkpoint is about 21.9 GB on disk and the
recipe marks it 32 GB minimum; the Inferact NVFP4 build is about 26.4 GB and also needs 32 GB.

The model cache belongs under `~/.cache/huggingface`, not `/model`. `/model` is neither required by
vLLM nor a meaningful machine-state path. Keep a separate launch wrapper and environment under
`~/.local/share/vllm-qwen38` so the model cache can be reclaimed independently.

The first launch should use the Red Hat recipe's parser/tool flags, one request at a time, and a
32K context is the current target; increase it only after observing `nvidia-smi`
and a real request. Do not download the checkpoint until the user explicitly approves the model
download and the NVIDIA device is visible to the process.

The initial launch shape is:

```sh
vllm serve RedHatAI/Qwen3.8-27B-INT4 \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --max-num-seqs 1 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml
```

## Requirements

* NVIDIA driver and device nodes working (`nvidia-smi` must report the GPU).
* Python 3.13 (system Python 3.14 is not assumed compatible with the vLLM wheel).
* `uv` for the isolated environment and package resolution.
* A vLLM build with Qwen3.8 and compressed-tensors W4A16 support, plus its CUDA/PyTorch
  dependencies.
* Approximately 25 GB free for the model and temporary download overhead, with additional VRAM
  for the vision encoder, runtime buffers, and KV cache.

## Verification

This record remains absent until the user-space environment and model are actually installed. The
safe checks are `nvidia-smi`, `uv run python -c 'import vllm'`, and a bounded health request to the
local server. They must not authenticate, open a GUI, or download a model as a side effect.
