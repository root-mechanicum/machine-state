# Strata

## Function

The local large model: Qwen3.8-Flash-Next (177B MoE) in ISTA-DASLab's GSQ-RCO IQ3_S quant, served by
Strata (`github.com/Niko1221/Strata`, MIT) on `127.0.0.1:8000`, the same port as the 27B servers.
Strata splits the experts across VRAM (hot cache), locked RAM and the CPU, which is what fits a
177B model on a 24 GB laptop GPU. It follows lifeidle's Flash-Next setup
(`github.com/lifeidle/qwen3.8-flash-next-5090-laptop-24gb-strata`, same RTX 5090 Laptop).

A **mode, not the default**: while it runs it holds about 47 of the 62 GB of RAM, so the desktop
keeps a terminal and Pi, not a browser. TWIN-TURBO 27B (`llama-cpp.md`) stays the login default.
Uses: deep sessions (reading, planning, review) and unattended batches of delegated beads.
Kept as a hedge against restricted or expensive hosted models. Tracked in bead `machine-state-cnh`.

## Installed state

* **App:** `~/.local/share/strata/app`, a clone of Strata at tag v0.2.12 (commit `146df3c`), whose
  `setup.sh`/`setup.py` were read before running (audit in the bead's notes). Setup made a `.venv`
  there with pinned Python packages and NVIDIA's cuBLAS/CUDA runtime wheels, and wrote
  `~/.config/strata/settings.json` (data dir). Nothing system-wide, no sudo.
* **Engine:** 0.1.58 for Linux x86_64 / CUDA 13, from Strata's signed update feed (built-in keys,
  every file checked against the signed manifest).
* **Model:** `~/.local/share/strata/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_S/`, two
  files, SHA-256 equal to Hugging Face's:
  `…-IQ3_S-00001-of-00002.gguf` 54,817,524,224 bytes `4c1eb2ce…aca3`,
  `…-IQ3_S-00002-of-00002.gguf` 28,800,138,432 bytes `316b46f3…e113`
  (the second is the same file as IQ3_XXS's second shard). Image reader
  `mmproj-Qwen3.8-Flash-Next-BF16.gguf` beside them. Packed for Strata in `~/.local/share/strata/packs/iq3_s`.
* **Speculative decoding:** the MTP draft layer, extracted by Strata from Qwen's BF16 checkpoint
  into `~/.local/share/strata/mtp/` (6.5 GB, per-tensor SHA-256 checked). It exists only in the
  354 GB BF16 checkpoint, so it is backed up with the models.
* **Backups:** the model files are copied to the WD Elements drive (`Models/<org>--<repo>/`).
* **Engine flags** live in `~/.local/share/strata/app/strata-iq3_s.json`, owned by Strata's setup.
  Two values changed from setup's defaults after lifeidle's measurements: `--spec 2` (setup: 4) and
  `--max-context 262144` (setup: 131072, with `--kv-resident 32768` keeping the KV in RAM).
  Setup's original is kept as `strata-iq3_s.json.setup-default`; re-running setup may rewrite it.

## Lifecycle

`canonical/strata/strata-flash-next.service`, projected to `~/.config/systemd/user/`. No `[Install]`:
it never starts at login. `Conflicts=llama-twin-turbo.service vllm-qwen38.service`, so starting it
stops the 27B server and starting that stops this. `RestartSec=90`: the engine releases its pinned
memory slowly and a restart within ~70 s fails, so wait that long before starting it again.

* Start: `systemctl --user start strata-flash-next` (ready in about 35 s). Since 2026-11-09 it runs
  `strata-iq3_s-resident.json` (`--resident-experts`: RAM holds only the experts the GPU does not):
  ~8 GB available instead of ~1, 106 tok/s instead of 136 on three long answers. The faster
  `strata-iq3_s.json` is unchanged beside it; the unit's `--config` picks one.
* The smaller quant: `systemctl --user start strata-flash-next-xxs`
  (`canonical/strata/strata-flash-next-xxs.service`, Pi `strata/qwen3.8-flash-next-iq3_xxs`).
  IQ3_XXS's shard 1 (47,039,860,096 bytes, `219ea929…6d15`) in `IQ3_XXS/`, shard 2 the same file
  as IQ3_S's; its own pack `packs/iq3_xxs` and config `strata-iq3_xxs.json` (setup run with
  `--gguf-dir` on that folder, `--context 262144`; `--spec` changed 4 → 2 to match IQ3_S; original
  kept as `.setup-default`). Same engine, MTP draft and image reader. The two modes conflict with
  each other and with the 27B servers, so starting one flips to it.
* Back to the default: `systemctl --user start llama-twin-turbo`.

Clients: Pi names it `strata/qwen3.8-flash-next-iq3_s` (`canonical/pi/models.json`: 262K window,
text and images, thinking levels low/medium/xhigh; "high" silently becomes xhigh). Strata accepts any
model name, so `/ask`, `/do` and `local-pi`, which name the 27B, work unchanged while it runs. It
serves OpenAI (`/v1/chat/completions`) and Anthropic (`/v1/messages`) APIs, with heartbeat events so
long silent phases do not trip 60 s client timeouts. Pass `max_tokens` ≥ 600: it thinks first.

## Measured (2026-11-08, engine 0.1.58, IQ3_S, spec 2, images on)

| | |
|---|---|
| Start to ready | ~35 s (46.84 GiB of experts locked at 5.16 GiB/s; 14.70 GiB VRAM expert cache) |
| RAM left for the desktop | ~2 GiB available (1.4 at a 252K prompt); swap steady, no OOM |
| VRAM | 22.3 GB |
| Decode | 109-133 tok/s; MTP draft acceptance ~75-97% |
| Prompt reading / time to first token | 31K: 10.1 s (3,118 tok/s) · 95K: 29.5 s (3,210) · 252K: 84.8 s (2,982) |
| Long context | a code hidden at 60% depth found at 31K, 95K and 252K |
| PCIe | Gen 5 x8 even at 100% GPU (how this laptop is wired); 0.5-2% of experts cross it once warm |
| GPU under load | max 174 W, 61 °C |
| Agent work | replay of rerule-wwu.7.1.2 in bwrap (same prompt and baseline as TWIN-TURBO, no worker.md): 10m10s, verify and test:firefox pass, 11/12 of the accepted tests (TWIN-TURBO 9/12); the one miss is a wording choice the bead does not fix |

## Verification

`systemctl --user is-active strata-flash-next`; `curl -s localhost:8000/v1/models` names
`qwen3.8-flash-next-iq3_s` with `n_ctx` 262144. The unit's journal shows the experts locked and
"ready"; each answer's `done:` line gives tok/s and the expert-cache hit rate. MTP is working only
if responses report accepted drafts (`draft_n_accepted` in the timings).
