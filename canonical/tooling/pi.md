# Pi

## Function

Local coding agent using a user-space Node.js installation and Pi's OpenAI-compatible model
configuration. Pi is an application-layer tool, not a substrate dependency.

## Intended setup

Use Pi's managed installer from `https://pi.dev/install.sh`. The installer currently requires
Node.js 22.19.0 or newer and npm. On Linux x86_64, if Node is absent, it selects the latest v22
`linux-x64` archive from Node's published `SHASUMS256.txt`, verifies the SHA-256 checksum, and
installs it under `${XDG_DATA_HOME:-$HOME/.local/share}/pi-node`.

The managed Pi release is resolved from `https://pi.dev/api/installer/releases/latest`, then its
versioned `package.json` and `package-lock.json` are installed with `npm ci --ignore-scripts`.
The canonical model configuration belongs at `~/.pi/agent/models.json`; it routes the `vllm`
provider to `http://localhost:8000/v1` and selects `RedHatAI/Qwen3.8-27B-INT4`.
The model exposes a 98,304-token context (matching vLLM's `--max-model-len`, which counts prompt
and output together) and a 65,536-token response ceiling, leaving about 32k tokens for the prompt.
The ceiling is large so `xhigh` reasoning can reach tool execution and a final response.

Thinking runs at `xhigh` everywhere. Pi's built-in default is `medium`, so the intended state is
`"defaultThinkingLevel": "xhigh"` in Pi-owned `~/.pi/agent/settings.json` (set 2026-11-01; Pi
writes that file itself, so it is recorded here rather than projected). Launchers also pass
`--thinking xhigh` (see `canonical/roles/roles.toml`), and `local-pi` hard-codes it, so they stay
at `xhigh` even if the setting is lost. Qwen3.8's chat template accepts only `xhigh` (its own
default), `medium` and `low`; the `thinkingLevelMap` disables `high`, so a request for `high`
clamps up to `xhigh`. Check the resolved level with an RPC `get_state` on a fresh Pi.

The current Pi-managed extensions are `pi-mono-context`, `pi-mono-context-guard`,
`pi-mono-multi-edit`, and `pi-mono-web-search`. Pi owns their package manifest and install
directory under `~/.pi/agent/npm`; this record documents the intended set without projecting over
Pi's package-manager state.

## Requirements

* Pi 1.3.0 or a later managed release.
* Node.js 22.19.0 or newer and npm.
* A running vLLM OpenAI-compatible server at `http://localhost:8000/v1`.
* The Qwen3.8 model served by vLLM with text and image input support.

## Verification

Check `node --version`, `pi --version`, and the rendered `~/.pi/agent/models.json`. Verify the
local endpoint with a bounded request only after vLLM is intentionally running; Pi configuration
must not download model weights or start the inference server as a side effect.
