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

## Pass 2 Tightening

The first controlled pass confirmed that `1d00f67be12c7d6a` reacts to deliberate movement, but it moved along the same apparent axis in both the east and north runs. Before running a second pass:

- keep the camera fixed for the whole run
- do not rotate the character or camera between moves if it can be avoided
- prefer one longer straight movement instead of many short corrections
- if the client supports keyboard movement, prefer that over click-to-move

Recommended second-pass labels:

- `walk-east-long`
- `walk-west-long`
- `walk-north-long`

The main goal is to see whether `1d00f67be12c7d6a` still changes only one field when the travel direction changes, or whether the first pass just happened to project multiple motions onto the same world axis.

## Target-Family Trace

After the normal frame, label, and movement-candidate generation, write focused traces for the main suspect families:

```powershell
python -c "from pathlib import Path; from emulator.tools.world_family_trace import write_world_family_trace_report; write_world_family_trace_report({'idle': Path(r'$($idle.FullName)'), 'walk-east': Path(r'$($east.FullName)'), 'walk-north': Path(r'$($north.FullName)')}, prefix_hex='1d00f67be12c7d6a', target=Path('captures/trace-1d00f67be12c7d6a'))"

python -c "from pathlib import Path; from emulator.tools.world_family_trace import write_world_family_trace_report; write_world_family_trace_report({'idle': Path(r'$($idle.FullName)'), 'walk-east': Path(r'$($east.FullName)'), 'walk-north': Path(r'$($north.FullName)')}, prefix_hex='1d004d23c18ad027', target=Path('captures/trace-1d004d23c18ad027'))"
```

Read:

- `captures/trace-1d00f67be12c7d6a/summary.md`
- `captures/trace-1d004d23c18ad027/summary.md`

Success criteria for pass 2:

- `1d00f67be12c7d6a` shows a clearly different dominant axis or different signed delta pattern between at least two directional runs
- or a neighboring entity-position family such as `1d004d23c18ad027` becomes the cleaner directional indicator

## Pass 3 Open-Area Recapture

The pass-2 long runs showed a new constraint: the current spawn location does not allow much clean travel in every direction. East-long still activated `1d00f67be12c7d6a`, but west-long and north-long left that family static and instead made `1d004d23c18ad027` much noisier. Treat that as useful evidence, but do not use those runs as the final direction-mapping proof.

Before the next controlled pass:

- manually relocate the character to a less constrained open floor area
- pick one visible floor marker or tile edge as the common start point
- keep the camera fixed for the whole set
- avoid turning before the directional click if keyboard movement still is not available

Recommended open-area labels:

- `open-idle`
- `open-east`
- `open-west`
- `open-north`

Success criteria for pass 3:

- `1d00f67be12c7d6a` either flips sign or switches dominant axis between open-area directional runs
- or `1d004d23c18ad027` cleanly separates one directional run from the others instead of merely becoming active under constrained pathing
- or both families prove that one is local-player motion while the other is nearby-entity or pathing feedback
