# macOS build, signing, and distribution

## Architecture artifacts

The GitHub Actions build produces two independent `.app` bundles:

- `macOS-arm64`: built on the Apple Silicon `macos-26` runner.
- `macOS-x86_64`: built on the Intel `macos-26-intel` runner.

These are architecture-specific applications, not a universal2 binary. Do not rename one artifact as the other. The bundle records the release version from `APP_VERSION` in `Info.plist`.

## What CI currently verifies

CI builds the app with PyInstaller in `onedir` mode, verifies the bundle's current code signature, runs the headless scientific self-check, and starts the actual Qt window in offscreen mode. PyInstaller's normal macOS build produces an ad-hoc signature when no Developer ID identity is configured. This is useful for build integrity checks, but it is **not** a Developer ID distribution signature and does not imply Gatekeeper approval or notarization.

## Developer ID signing and notarization

Public distribution outside controlled testing should use an Apple Developer ID Application certificate and notarization. The repository does not contain signing credentials, and CI must not invent or commit them. Before enabling automated signing, configure protected GitHub Actions secrets for the certificate (`.p12` base64), its password, and the App Store Connect API credentials used by `notarytool`. Keep those secrets scoped to protected release workflows/environments.

Recommended release sequence on macOS:

1. Import the Developer ID Application certificate into a temporary keychain on the runner.
2. Build/sign the `.app` with the Developer ID identity and Hardened Runtime enabled. Preserve the nested-code signatures; do not run UPX over macOS binaries.
3. Verify the complete bundle with `codesign --verify --deep --strict --verbose=2 PulsarLab.app`.
4. Create a ZIP that preserves bundle symlinks (`ditto -c -k --sequesterRsrc --keepParent PulsarLab.app PulsarLab-macOS.zip`).
5. Submit that ZIP using `xcrun notarytool submit ... --wait`, then staple the ticket with `xcrun stapler staple PulsarLab.app`.
6. Validate with `spctl --assess --type execute --verbose=4 PulsarLab.app` and re-run the application smoke test.

The current build pipeline intentionally stops before Developer ID signing/notarization until the project owner configures Apple credentials and approves the release environment.

## Minimum OS version

The app is built on macOS 26 runners. This validates the current runner OS, not every older macOS release. Define an oldest supported macOS version only after testing on that version; otherwise document compatibility as unverified for older releases.
