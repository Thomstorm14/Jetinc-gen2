# JETinc — Live Handoff State

READ THIS FILE FIRST, BEFORE DOING ANYTHING ELSE.

## Rule for every AI reading this file
Never write "done," "fixed," "working," or add anything to the Trident Ledger
unless you have run a real command and can show its exact output as proof.
If you did not run the command yourself in this session, say "not verified"
instead of guessing or assuming it works. A false "done" here costs Thom real
time later — treat that as a serious error, not a shortcut.

When you finish a step, update this file yourself: move it from "Next Task"
to "Verified Done," and paste the exact command + exact output you got as
proof. Do not describe what you think happened — paste what actually printed.

## Verified Done
- 2026-09-30: Pushed Gen 1 codebase from SanDisk (D:\GenOne_Backup\JETinc\
  JETcity_Launchpad\jetinc_build) to GitHub branch `gen1-import` on
  Thomstorm14/Jetinc-gen2. Proof: `git push origin gen1-import` output showed
  "* [new branch] gen1-import -> gen1-import", 78 objects, 141.75 KiB.
- 2026-09-30: Installed Ollama + pulled gemma3:4b on this laptop. Proof:
  `ollama run gemma3:4b "Say ready if you're working."` returned "Ready! 😊"

## Next Task (exactly one — do not start a second task until this is proven done)
Rewrite `qwen_client.py` (currently calling Qwen 2.5 0.5B) to call Gemma 3 4B
through Ollama's local API instead (http://localhost:11434). Do not touch
any other file. Do not rewrite genone.py, ledger.py, or prime_registry.py.
When done, prove it by running genone.py once and pasting its real terminal
output here, not a description of what it should output.

## Known real files (confirmed to exist and contain real code)
- genone.py — main consensus engine
- agents/ledger.py — TridentLedger, SHA-256 chained
- agents/prime_registry.py — Prime ID system
- qwen_client.py — currently calls Qwen 2.5 0.5B, needs to be repointed at Gemma

## Known open problems (not yet fixed)
- Task 10 times out during stress testing — suspected cause: genone.py's
  phases run agents concurrently within a phase but phases themselves run
  sequentially (OR -> grade -> comerge -> merge -> vote), so total time
  compounds. Not yet confirmed which exact phase is slow.
- Autoindexer (separate Google Apps Script, not part of this repo) has its
  own timeout fix already applied in a prior session — not yet re-verified.

## Still undefined (need Thom's input before building, do not guess)
- Mirror group email bus — exact behavior unspecified
- Communication Hub — unclear if same as "Communication Neural Network"
  mentioned in older notes
- Command Center dashboard — no file yet, not started
