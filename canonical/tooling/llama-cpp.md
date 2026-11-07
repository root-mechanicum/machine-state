# llama.cpp

## Function

Second local inference server, beside vLLM: Qwen3.8-27B in the TWIN-TURBO NVFP4 fine-tune, served
by `llama-server` on `127.0.0.1:8000` (OpenAI-compatible), the same port as vLLM. It follows lifeidle's "route T"
(`github.com/lifeidle/qwen3.8-27b-5090-laptop-24gb-coder390-ninfer`, measured on the same RTX 5090
Laptop 24 GB): about 74-78 tok/s with the model's own MTP draft head, 160K context. An
application-layer experiment, not a substrate dependency. Tracked in bead `machine-state-0ms`.

## Installed state

* **Engine:** the prebuilt release `b12189` (commit `80d2c0c2c`), not a source build. Archives
  `llama-b12189-bin-ubuntu-cuda-13.5-x64.tar.gz` and `cudart-llama-b12189-bin-ubuntu-cuda-13.5-x64.tar.gz`
  from `github.com/ggml-org/llama.cpp/releases`, SHA-256 checked against the release's published
  digests, unpacked into `~/.local/share/llama.cpp/releases/b12189/`. `~/.local/share/llama.cpp/bin`
  is a symlink to the active release, so an upgrade is unpack-then-relink and a rollback is a relink.
  The bundled CUDA 13.5 runtime runs on driver 615.78.08 (CUDA 13.4); `llama-server --list-devices`
  lists the RTX 5090. No system CUDA toolkit or cmake is needed.
* **Source:** `~/src/llama.cpp` is a plain clone for reading and for a patched build if one is ever
  needed. The service does not run from it.
* **Model:** `~/.local/share/llama.cpp/models/esatapedico/Qwen3.8-27B-TWIN-TURBO-NVFP4-GGUF/`,
  file `…-Uncensored-NVFP4-MID-HIGH.gguf`, 16,912,387,360 bytes, SHA-256
  `ed2d2e482d770b682376dba28c63e9711f61aa1a77a1a5d48c1eaa8a7d6f9063` (matches Hugging Face).
  Base model DavidAU/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-Uncensored, Apache-2.0 per its
  card. It is an **uncensored community fine-tune**, not stock Qwen: it refuses less, so agent use
  leans on `dcg` and on `/do`'s approval step.

## Lifecycle

`canonical/llama-cpp/llama-twin-turbo.service`, projected to `~/.config/systemd/user/`. It has
`Conflicts=vllm-qwen38.service`, so starting either server stops the other; the GPU holds one.
It has no `[Install]` section: vLLM stays the login default and this one is started by hand.
`ConditionACPower=true`, as for vLLM.

**Port 8000 is the contract, not the engine.** `cap`'s `model:local` channel, `/ask`, `/do` and the
agents talk to whatever answers on `127.0.0.1:8000`; `cap` reads the model name from `/v1/models`.
`llama-server` serves its single model whatever name a request carries, so launchers in
`canonical/roles/roles.toml` that pin `vllm/RedHatAI/Qwen3.8-27B-INT4` keep working on either
server, with vLLM's more conservative 98K window. Pi can also name this model directly as
`llamacpp/qwen3.8-27b-twin-turbo` (160K window).

## Measured (2026-11-07, b12189, warm page cache)

| | vLLM INT4 | llama.cpp TWIN-TURBO |
|---|---|---|
| Load to healthy | ~2 min | 2.7 s (cold load from NVMe not measured) |
| Decode, short question | ~35 tok/s | 77-92 tok/s, MTP acceptance 56-72% |
| Prompt reading | — | 2,800-2,900 tok/s; repeated prefix reused (66 → 4 tokens) |
| `pi -p` "pong" | — | 2.7 s |
| `/ask`-style run with a cap tool call | — | 4.9 s, tool call round trip confirmed |
| VRAM at 160K | ~22 GB | 22.9 GB used, 1.1 GB free |

## Verification

`~/.local/share/llama.cpp/bin/llama-server --version` and `--list-devices`; once the service runs,
`curl -s localhost:8082/v1/models` and a bounded chat request. MTP is working only if the server
log reports accepted drafts.
