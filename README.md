> [!WARNING]
>  Deprecated CI scripts, I don't like piracy

### Can I play with an APK?

No, this allowed piracy that is forbidden in this project.

Any attempt to document workarounds or make it easy to import an paid apk without a valid google play game license is undesirable.

Game licenses can be revoked at any point of time by you, microsoft/mojang or google, as it happened for all residents of Russia.

Ignoring this policy may cause suspension including termination of this project like happended between 2022-2023.

_Exception to the rule are Minecraft Trial and Edu where the latter doesn't work at this time._

For the most current version of this rule see https://minecraft-linux.github.io/faq/index.html#can-i-play-with-an-apk


## macOS Troubleshooting & Performance Optimization

### ANGLE & Metal Backend Setup
- On macOS Apple Silicon (M1/M2/M3/M4) and Intel Macs, ANGLE translates GLES graphics calls via Metal or OpenGL.
- To enable the native Metal backend override, set:
  ```bash
  ANGLE_DEFAULT_PLATFORM=metal
  ```
- For GPU rendering compatibility on Bedrock, you can pass:
  ```bash
  force_gl_renderer="Adreno (TM) 740"
  ```

### Xbox Live / MSA Authentication
- Ensure `libcurl` version is 8.21.0 or newer to prevent ECDSA token verification errors on `sisu.xboxlive.com`.
- If login code "Drowned" occurs, clear stale auth cache tokens in `~/Library/Application Support/mcpelauncher/pass.token`.
