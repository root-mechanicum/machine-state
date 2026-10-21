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

## Requirements

* Pi 1.3.0 or a later managed release.
* Node.js 22.19.0 or newer and npm.
* A running vLLM OpenAI-compatible server at `http://localhost:8000/v1`.
* The Qwen3.8 model served by vLLM with text and image input support.

## Verification

Check `node --version`, `pi --version`, and the rendered `~/.pi/agent/models.json`. Verify the
local endpoint with a bounded request only after vLLM is intentionally running; Pi configuration
must not download model weights or start the inference server as a side effect.
