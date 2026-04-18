Laghaim / Savage Eden / Biosfear setup notes

Date verified: 2026-04-18

Client

- Source page: https://laghaimnew.com/MAIN_/download.php
- File name: `LaghaimOnlineNew.zip`
- Downloaded archive: `C:\Users\skull\OneDrive\Documents\savage eden\client\LaghaimOnlineNew.zip`
- Extracted client: `C:\Users\skull\OneDrive\Documents\savage eden\client\LaghaimOnlineNew`
- SHA256: `757BF57BED63C391420BE28B0B5393D59BD48E04D79095C929FDA2BD79587E1B`

Verified client files

- `Game.exe`
- `KP_Release_Game.exe`
- `LAUNCHER_PLAY.exe`
- `Laghaim_Update.dll`
- `SvrList.dta`
- `SvrListM.dta`

Server package status

- I did not find a verified free/public server package.
- The only server package I could confirm is a paid third-party checkout at `https://lh-dev.net/buy/`.
- Because the server package itself is not publicly downloadable from a clearly authorized source, the server install is blocked until a legitimate package is provided.

Verified server prerequisites from the public setup guide

Source: `https://lh-dev.net/setupguide/`

Windows

- Requires XAMPP or a MySQL/MariaDB setup.
- Databases listed in the guide:
  - `kor_ndev_neogeo_data`
  - `kor_ndev_neogeo_user`
  - `kor_ndev_neogeo_event`
  - `kor_ndev_neogeo_char`
  - `neogeo_web`

Linux

- Ubuntu guide installs 32-bit runtime libraries and `gdb`.
- CentOS guide installs MariaDB, PHP, phpMyAdmin, and Apache.
- The guide says to check:
  - `/config/config.json`
  - `/config/messenger_config.json`
  - `/config/packet_sniffing.json`

Ports listed in the guide

- TCP `4001`
- TCP `4002`
- TCP `4003`
- TCP `4004`
- TCP `4005`
- TCP `4006`
- TCP `4007`
- TCP `4008`
- TCP `4009`
- TCP `4010`
- TCP `4021`
- TCP `4022`
- TCP `4023`
- TCP `4024`
- TCP `4025`
- TCP `4026`
- TCP `4027`
- TCP `4028`
- TCP `4029`
- TCP `4030`
- TCP `4031`
- TCP `4032`
- TCP `4033`
- TCP `4034`
- TCP `4035`
- TCP `4036`

Guide note

- The setup guide says to keep port `4011` closed unless the default packet encryption key has been changed.

What is ready now

- The client archive is downloaded.
- The client is extracted and ready for inspection or launch.

What is still needed

- A legitimate server package containing the server binaries/source and the database SQL dumps.
- Once that package is available locally, the next step is to create/import the databases and patch the client/server connection details.
