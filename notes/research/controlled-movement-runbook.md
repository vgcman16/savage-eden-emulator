# Controlled Movement Runbook

This runbook is for the first deliberate movement-correlation pass against the live upstream server through the localhost capture shim.

## Goal

Capture a small set of labeled runs that make it easy to compare:

- standing still
- walking east
- walking north

The current analysis already suggests that `1d00f67be12c7d6a` is the strongest fine-movement candidate and that `1d004d23c18ad027` / `1d00b45f47d593c6` are likely nearby entity-position streams. This runbook is designed to confirm or reject that with cleaner evidence.

## Runner Commands

Use the existing working localhost proxy configuration and give each run a distinct label.

Idle run:

```powershell
python -m emulator.runner `
  --capture-root captures `
  --run-label idle `
  --http-port 18080 `
  --login-port 14021 `
  --proxy-host 79.137.101.33 `
  --proxy-port 4005 `
  --extra-proxy 4007:4007 `
  --extra-proxy 4008:4008
```

East-walk run:

```powershell
python -m emulator.runner `
  --capture-root captures `
  --run-label walk-east `
  --http-port 18080 `
  --login-port 14021 `
  --proxy-host 79.137.101.33 `
  --proxy-port 4005 `
  --extra-proxy 4007:4007 `
  --extra-proxy 4008:4008
```

North-walk run:

```powershell
python -m emulator.runner `
  --capture-root captures `
  --run-label walk-north `
  --http-port 18080 `
  --login-port 14021 `
  --proxy-host 79.137.101.33 `
  --proxy-port 4005 `
  --extra-proxy 4007:4007 `
  --extra-proxy 4008:4008
```

## In-Game Script

Keep the character in the same zone and start from the same visible floor location if possible.

For each run:

1. Log in and enter the world.
2. Wait still for about 5 seconds after loading finishes.
3. Perform only the run-specific action.
4. Wait still for about 5 seconds again.
5. Close the client, then stop the runner.

Per-run action:

- `idle`: do not move at all
- `walk-east`: move in one clean eastward line for about 8 to 12 short steps
- `walk-north`: move in one clean northward line for about 8 to 12 short steps

Avoid:

- camera spinning
- combat
- NPC interaction
- inventory actions
- map changes
- chat input

## Post-Run Analysis

Resolve the newest labeled runs:

```powershell
$idle = Get-ChildItem captures -Directory -Filter '*-idle' | Sort-Object Name | Select-Object -Last 1
$east = Get-ChildItem captures -Directory -Filter '*-walk-east' | Sort-Object Name | Select-Object -Last 1
$north = Get-ChildItem captures -Directory -Filter '*-walk-north' | Sort-Object Name | Select-Object -Last 1
```

Generate the frame index, family labels, and movement candidates for each run:

```powershell
python -c "from pathlib import Path; from emulator.tools.frame_index import write_frame_index; p=Path(r'$($idle.FullName)'); write_frame_index(p, p/'frame-index')"
python -c "from pathlib import Path; from emulator.tools.world_family_labels import write_world_family_labels; p=Path(r'$($idle.FullName)'); write_world_family_labels(p, p/'world-family-labels')"
python -c "from pathlib import Path; from emulator.tools.world_movement_candidates import write_world_movement_candidates; p=Path(r'$($idle.FullName)'); write_world_movement_candidates(p, p/'world-movement-candidates')"

python -c "from pathlib import Path; from emulator.tools.frame_index import write_frame_index; p=Path(r'$($east.FullName)'); write_frame_index(p, p/'frame-index')"
python -c "from pathlib import Path; from emulator.tools.world_family_labels import write_world_family_labels; p=Path(r'$($east.FullName)'); write_world_family_labels(p, p/'world-family-labels')"
python -c "from pathlib import Path; from emulator.tools.world_movement_candidates import write_world_movement_candidates; p=Path(r'$($east.FullName)'); write_world_movement_candidates(p, p/'world-movement-candidates')"

python -c "from pathlib import Path; from emulator.tools.frame_index import write_frame_index; p=Path(r'$($north.FullName)'); write_frame_index(p, p/'frame-index')"
python -c "from pathlib import Path; from emulator.tools.world_family_labels import write_world_family_labels; p=Path(r'$($north.FullName)'); write_world_family_labels(p, p/'world-family-labels')"
python -c "from pathlib import Path; from emulator.tools.world_movement_candidates import write_world_movement_candidates; p=Path(r'$($north.FullName)'); write_world_movement_candidates(p, p/'world-movement-candidates')"
```

Compare idle vs movement:

```powershell
python -c "from pathlib import Path; from emulator.tools.world_movement_compare import write_world_movement_comparison; write_world_movement_comparison(Path(r'$($idle.FullName)'), Path(r'$($east.FullName)'), Path('captures/compare-idle-vs-east'), baseline_label='idle', candidate_label='walk-east')"
python -c "from pathlib import Path; from emulator.tools.world_movement_compare import write_world_movement_comparison; write_world_movement_comparison(Path(r'$($idle.FullName)'), Path(r'$($north.FullName)'), Path('captures/compare-idle-vs-north'), baseline_label='idle', candidate_label='walk-north')"
```

## Expected Payoff

After these runs, the most useful files should be:

- `captures/compare-idle-vs-east/summary.md`
- `captures/compare-idle-vs-north/summary.md`
- each run's `world-movement-candidates/summary.md`

The best confirmation signal would be:

- `1d00f67be12c7d6a` becoming more movement-like in `walk-east` and `walk-north` than in `idle`
- the `x` span growing mostly in the east run
- the `y` span growing mostly in the north run
- nearby `1d004d23c18ad027` / `1d00b45f47d593c6` changes tracking the same movement windows
