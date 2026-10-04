# Frost Fed Bunker

Android FROST threshold signer and NIP-46 bunker for Glowstr/Nostr, built on the pinned Rust `keep` cryptographic core and Keep Android signer.

This repo contains a small, auditable Android overlay rather than a rewrite of the FROST cryptography.

## What works

- Rust FROST core on Android through UniFFI/JNI
- Distributed key generation (DKG)
- 2-of-3, 3-of-5, and custom threshold groups
- Advanced offline trusted-dealer generation on one device
- Encrypted `kshare1...` share exports
- Animated QR export/import for large share payloads
- Android Keystore + biometric-protected share storage
- NIP-46 bunker remote signing
- NIP-55 Android signer support
- NIP-44 encryption/decryption
- Signing permissions, audit history, and kill switch
- Glowstr can connect using the group npub + generated `bunker://` URL

## Recommended setup: distributed DKG

Distributed DKG is the preferred mode. Each signer generates its own contribution on the device that will hold the share, so no single device ever holds the complete private key.

Typical 2-of-3 setup:

1. Install Frost Fed Bunker / Igloo Mobile on three signer instances.
2. Configure the same secure `wss://` FROST relay.
3. On the coordinator choose **Create FROST Identity**.
4. Choose 2-of-3.
5. Exchange setup, subkey, and roster QR codes.
6. Complete DKG.
7. Each signer stores only its own share.
8. Enable NIP-46 Bunker on one signer.
9. Copy/show the `bunker://` URL.
10. In Glowstr use **FROSTR THRESHOLD SIGNER** with the group npub and bunker URL.

## Advanced setup: generate all shares offline

The app also exposes the Rust core's trusted-dealer `frostGenerate()` path.

This generates a fresh FROST identity and every encrypted share on one Android device. It is intended for an offline/air-gapped setup device.

The UI:

- defaults to 2-of-3
- supports custom thresholds
- requires an export passphrase
- displays the resulting group npub
- displays each encrypted share one at a time
- uses animated QR frames when needed

**Security warning:** during trusted-dealer generation, the generating device temporarily has enough key material to create all shares. Distributed DKG is stronger because the complete key never exists on one device.

The first implementation intentionally does not expose existing-`nsec` splitting in the Android UI.

## Pinned upstream revisions

- Keep Android: `f0db28aa218f18b71be60e3b1cf39eb51705e791`
- Keep Rust core: `d9192f5801949700dbefff2c9634b0fe904edf9e`

CI verifies the Android source and Rust core pins before building.

## Android build

The GitHub Actions workflow:

`.github/workflows/android.yml`

clones the pinned upstream projects, applies `apply-overlay.py`, compiles the Rust core for ARM64 Android, builds the APK, verifies the APK signature, and publishes a direct GitHub prerelease asset.

Current test package ID:

`org.glowstr.igloomobile`

## Share format compatibility

The current Rust core exports shares as `kshare1...`.

We have **not** established byte-for-byte compatibility with Bifrost/Igloo `bfshare1...` or `bfgroup1...` formats. Glowstr interoperability currently uses NIP-46, so Glowstr does not need to import the FROST share format itself.

## Status

Prototype / test software. Do not treat this as a completed third-party security audit.

See `THIRD_PARTY_NOTICES.md` for upstream attribution.
