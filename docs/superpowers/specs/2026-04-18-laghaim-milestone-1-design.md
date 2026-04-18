# Laghaim Milestone 1 Design

**Date:** 2026-04-18

**Topic:** Stock launcher/client compatibility shim for local server discovery and captured login-path progression

## Goal

Build a small local emulator stack that gets the stock `LAUNCHER_PLAY.exe` and `Game.exe` to talk to localhost, report the server as online, and advance through the first login boundary using scripted replies or an upstream proxy while capturing every request and response needed for later milestones.

## Scope

This milestone covers only the minimum compatibility needed for launcher discovery and login.

Included:

- Local service startup and orchestration
- Launcher status/update probe compatibility
- Local login gateway compatibility
- Scripted replay and upstream proxy modes for the login path
- Request/response packet capture
- Stubbed login success path

Excluded:

- Character list
- Character creation
- Zone/world simulation
- Movement
- Combat
- Database persistence
- Account management beyond temporary stub state

## Architecture

The milestone-1 system is a small `Python` compatibility stack that treats the existing launcher and game binaries as opaque clients. Instead of attempting to re-create the entire original server protocol up front, the stack focuses on satisfying only the earliest launcher and login expectations while recording all traffic for future protocol work.

The architecture has four parts:

1. `runner`
   Starts all local services, prints the active endpoints, and creates a run-specific capture directory.
2. `launcher probe`
   Handles the launcher's HTTP or status checks so the launcher believes the server is online and does not require an update.
3. `login gateway`
   Accepts the game's login connection, records the handshake, and can either return scripted responses or proxy the upstream login server while preserving local captures.
4. `trace logger`
   Writes structured raw packet logs, decoded notes, and per-run observations for later milestones.

## Why Python

`Python` is the best fit for milestone 1 because the work is dominated by socket iteration, packet logging, binary framing experiments, and quick protocol adjustments. The first milestone is a reverse-engineering loop rather than a product UI problem, so faster byte-level iteration matters more than ecosystem breadth.

## Current Client Findings

The extracted client folder already gives us useful anchors:

- `LAUNCHER_PLAY.exe` appears to be a .NET/WPF launcher.
- Launcher strings show `ServerIP`, `CSPort`, `GSPort`, `HttpWebRequest`, `HttpWebResponse`, `CheckPort`, `SelfUpdate`, and `SERVER ONLINE!`.
- `explorer.txt` contains `www.laghaimnew.com`.
- `SvrList.dta` and `SvrListM.dta` are present but appear encoded or obfuscated, not plain text.
- The launcher likely performs both HTTP and TCP checks before starting the game.

These findings support a split between launcher compatibility services and the game login gateway.

## Compatibility Strategy

The milestone-1 strategy is:

**Instrument first, emulate second.**

We will not assume we already know the auth packet format. Instead, we will build a local compatibility shim that captures actual launcher/client behavior and then implement only the minimum handlers required for the approved success path.

The compatibility layers are:

1. `endpoint redirect`
   Point launcher and client traffic at localhost using the lightest workable mechanism.
2. `transport capture`
   Log every TCP and HTTP request/response before decoding.
3. `message framing`
   Determine whether traffic is fixed-size, length-prefixed, compressed, encrypted, or XOR-obfuscated.
4. `minimal handlers`
   Implement only the request/response pairs needed for launcher online status, update bypass, login handshake, scripted replay, and upstream proxy capture when pure stubbing is not yet sufficient.

## Redirection Policy

Preferred order:

1. Editable local config already used by launcher/client
2. Minimal local wrapper or startup behavior
3. Hosts-file or domain redirection only if necessary

The first attempt should preserve the stock launcher and stock client behavior with as little patching as possible.

## Fallback Policy

If the launcher blocks progress because of self-update logic:

- Return a local "no update required" response

If the first stubbed login response does not advance the client:

- Add an upstream proxy mode so localhost stays in the loop while we capture the real post-auth exchange

If launcher and game traffic use different ports or protocols:

- Keep them as separate services

If the login protocol is obfuscated:

- Milestone 1 still succeeds if we can capture it, characterize the framing, and preserve a working proxied login path for deeper packet collection

If the launcher requires the original website domain:

- Add the minimum local redirection needed, but keep the emulator itself domain-agnostic

## File Layout

Planned project structure:

```text
docs/
  superpowers/
    specs/
      2026-04-18-laghaim-milestone-1-design.md

emulator/
  __init__.py
  runner.py
  config.py
  services/
    __init__.py
    http_probe.py
    login_gateway.py
  protocol/
    __init__.py
    framing.py
  logging/
    __init__.py
    trace_writer.py

captures/
  <run-id>/
    summary.md
    launcher-http.log
    login-gateway.log
    packets/
      *.bin
      *.hex.txt

notes/
  research/
    milestone-1-observations.md
```

## Component Responsibilities

### `emulator/runner.py`

- Start and stop the local services
- Allocate capture directories
- Print the active endpoints to use with the client
- Coordinate shared runtime state

### `emulator/config.py`

- Store bind address
- Store launcher probe port
- Store login gateway port
- Store paths to client binaries and capture directories
- Hold toggles for redirection and verbose tracing

### `emulator/services/http_probe.py`

- Listen for launcher HTTP requests
- Respond to update/status probes
- Return "online" and "no update required" compatible responses
- Log full request and response pairs

### `emulator/services/login_gateway.py`

- Listen for the game's login connection
- Capture inbound packets
- Identify basic framing
- Return the minimum stubbed success sequence required by the client
- Log all request/response data and any disconnect reason

### `emulator/protocol/framing.py`

- Hex formatting helpers
- Length-prefix parsing helpers
- Byte diff helpers for repeated runs
- Simple XOR or obfuscation experiments if needed
- Replay-safe message wrappers

### `emulator/logging/trace_writer.py`

- Write per-run structured logs
- Write raw binary packet files
- Write hex dumps and packet indexes
- Keep timestamps and connection metadata

## Data Flow

Expected milestone-1 flow:

1. Start emulator runner
2. Runner starts launcher probe service
3. Runner starts login gateway service
4. Launcher is pointed at localhost
5. Launcher performs status/update probe
6. Launcher sees server as online
7. Launcher starts game
8. Game opens login connection to local gateway
9. User enters username/password
10. Emulator captures login handshake
11. Emulator returns a scripted or proxied response sequence
12. Capture artifacts are written for milestone 2

## Logging and Research Output

Every run should produce:

- A timestamped run directory
- HTTP probe logs
- Login connection logs
- Raw packet captures
- Hex dumps
- A short human-readable summary of what happened

Each run summary should answer:

- Which endpoints were active
- Did the launcher contact the probe service
- Did the launcher report the server online
- Did the game reach the login connection
- What packets were observed
- Did the client accept the scripted or proxied login path
- Where did it fail if it did not fully succeed

## Definition of Done

Milestone 1 is complete when all of the following are true:

- We can start the emulator with one command
- The stock launcher can be directed to localhost by config or a minimal redirection step
- The launcher shows the server as online
- The stock client reaches the login flow against the local emulator
- Entering a username/password produces a real captured login exchange
- The emulator can return scripted responses or proxy the upstream login flow without losing local captures
- The full launcher and login request/response path is logged for later milestones

## Risks

### Unknown launcher probe format

The launcher may expect specific HTTP payloads or status markers.

Mitigation:

- Capture first
- Emulate only the minimal shape it actually requests

### Encoded or obfuscated server list data

`SvrList.dta` and `SvrListM.dta` are not plain text.

Mitigation:

- Prefer launcher config or runtime discovery first
- Treat encoded server list files as secondary reverse-engineering targets

### Client login encryption or custom framing

The login path may use XOR or custom packet structure.

Mitigation:

- Build framing helpers first
- Log multiple repeated runs with controlled inputs

### Client assumes launch from its installation root

The stock client reads language and UI data through relative paths such as `data/menu/str/US.txt`.

Mitigation:

- Start `Game.exe` with the extracted client directory as the working directory
- Use Ghidra-backed string and xref tracing when a popup suggests a missing local asset rather than a network failure

### Launcher hard dependency on original website

The launcher may insist on contacting the original domain.

Mitigation:

- Use the least invasive redirection mechanism that works
- Keep local services able to impersonate only the required endpoints

## Checkpoint List

This list is intentionally written as a checklist so milestone progress can be tracked directly from the spec.

- [x] Approve milestone-1 scope: stock launcher/client, server online, stubbed login success
- [x] Approve architecture: runner, launcher probe, login gateway, trace logger
- [x] Approve compatibility strategy: instrument first, emulate second
- [x] Approve milestone-1 file layout and logging plan
- [x] Create initial emulator project skeleton
- [x] Implement runner and shared config
- [x] Implement launcher HTTP/status probe
- [x] Verify launcher reports local server as online
- [x] Implement login gateway socket listener
- [x] Capture first raw login handshake from stock client
- [x] Characterize message framing for login path
- [x] Implement stubbed login success response
- [ ] Verify stock client accepts stubbed login path
- [x] Add upstream proxy mode for continued localhost packet capture
- [x] Verify stock client can log in and reach character flow through localhost proxying
- [x] Verify stock client can enter the world through localhost proxying
- [x] Identify and fix the client working-directory requirement for local data files
- [x] Mitigate the Intel iGPU world-load crash by forcing `Game.exe` onto the discrete GPU
- [x] Save complete capture artifacts for milestone 2
- [x] Write milestone-1 research summary with packet notes

## World Stream Discovery Queue

This follow-on checklist tracks the first reverse-engineering steps after milestone 1 so world-emulation work can keep moving in small, checkable slices.

- [x] Prove that captured `14021` TCP chunks can be split into protocol frames using the leading little-endian length field
- [x] Generate a frame-aware family index for the successful in-world capture
- [ ] Label the top repeated world-frame families by likely role
- [ ] Correlate coordinate-like frames with controlled in-game movement and map interactions
- [ ] Build the first standalone scripted or stubbed reply for one repeated world-frame family

## Out of Scope Reminder

The following remain explicitly deferred:

- Character list and selection
- Character creation
- Persistent accounts
- Game world and maps
- NPC logic
- Combat and movement
- Inventory and items
- Database schema reconstruction

## Spec Self-Review

Review completed inline against the approved conversation:

- No placeholder sections remain
- Scope is intentionally limited to one milestone
- Architecture, data flow, and definition of done are aligned
- The checkpoint list reflects the approved milestone boundary

