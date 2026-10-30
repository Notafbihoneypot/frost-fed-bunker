# Frost Fed Bunker

Android FROST threshold signer and NIP-46/NIP-55 signer for Glowstr/Nostr, built as a small overlay on pinned Keep Android and Keep Rust revisions.

The project intentionally reuses the upstream FROST implementation instead of reimplementing threshold cryptography in Kotlin.

## Current 0.3.0 hardening base

- Keep Android: `50c70f2cbe67eac7e289e4950625f34f2c038fc1`
- Keep Rust core: `2ebfed2086688ab880ff0f58bb8f7c7dd3acaf9e`
- Android package: `org.glowstr.frostfedbunker`

The Rust revision above is the exact `keep.version` pinned by the Android revision. We deliberately keep the pair coherent instead of mixing a newer Rust API into an Android revision that has not adopted it yet.

## What works

- Rust FROST core through UniFFI/JNI
- Distributed FROST DKG
- 2-of-3, 3-of-5, and custom threshold groups
- Advanced offline trusted-dealer share generation
- Encrypted `kshare1...` share export/import
- QR and animated-QR share transfer
- Save encrypted share backups as `.kshare` files
- Explicit paste/QR `nsec1...` account import
- Android Keystore + biometric-protected local storage
- NIP-46 bunker remote signing
- NIP-55 Android signer support
- NIP-44 encryption/decryption
- Approval notifications without forced full-screen/activity launch
- Signing permissions, history, audit data, and kill switch
- NIP-46 client revoke and bunker credential rotation
- Offline full-set FROST share refresh/rotation
- Crash diagnostics
- Back/cancel handling for transient signer screens

## Recommended setup: distributed DKG

Distributed DKG is the preferred setup because no one device ever needs the complete signing secret.

Typical 2-of-3 setup:

1. Install Frost Fed Bunker on three signer instances.
2. Configure the same secure `wss://` FROST coordination relay(s).
3. On the coordinator choose **Create Signing Group**.
4. Choose **2 of 3**.
5. Exchange the setup, subkey, and roster QR data.
6. Complete DKG.
7. Each signer keeps only its own share.
8. Configure the separate **Bunker Relays** list on the signer serving NIP-46.
9. Enable the NIP-46 bunker.
10. Pair Glowstr with the generated `bunker://` URL and group npub.

FROST coordination relays and NIP-46 bunker relays are separate settings.

## FROST share rotation

**Rotate FROST Shares** performs an offline full-set refresh:

- the group npub stays the same;
- every signing share changes;
- the complete current share set is required;
- duplicate or missing share identifiers are rejected by the Rust core;
- the core uses checked randomness for the refresh;
- each refreshed secret share is checked against its published verifying share before output;
- old and new shares must never be mixed.

The Android rotation screen accepts either one current export passphrase for every input share or one passphrase per line/share. After rotation, every refreshed share can be shown as QR and saved individually as a `.kshare` file.

**Security tradeoff:** this UI performs full-set rotation on one trusted device, so that device temporarily receives every encrypted share and decrypts the full set. Prefer doing it on a trusted offline device. This is not a distributed proactive-refresh protocol.

## NIP-46 bunker credential rotation

**Rotate NIP-46 connection keys** is separate from FROST share rotation.

It changes the bunker transport/connect credentials and invalidates the previously distributed `bunker://` URL. Existing clients must re-pair with the newly generated URL. It does not change the FROST group npub or FROST signing shares.

Client revocation and account switching use the hardened upstream revoke/rotation paths rather than a separate Frost Fed Bunker cryptographic implementation.

## Advanced offline trusted-dealer generation

The app also exposes the Rust core trusted-dealer generation path. It can generate all shares on one Android device for later distribution.

This is useful for an intentionally offline setup device, but it is weaker operationally than distributed DKG because one device temporarily handles the complete threshold material.

## nsec import

An existing `nsec1...` can be imported as a normal single-key signer account using **Import / paste nsec** or QR scanning. The explicit Paste action validates the NIP-19 nsec format and clears the Android clipboard after a successful paste.

Importing an nsec does **not** convert that account into a FROST group or split the nsec into threshold shares.

## Relay behavior

A distributed FROST signature requires enough participants to communicate. If one public relay fails, configure multiple relays for redundancy.

The current upstream transport is relay/network based. A fully disconnected FROST signing flow would require a separate local/air-gap transport (for example LAN or multi-round animated QR); that is not claimed as implemented here.

## Android build

The GitHub Actions workflow is:

`.github/workflows/android.yml`

It:

1. checks out the exact pinned Keep Android and Rust pair;
2. applies `apply-overlay.py`;
3. verifies critical hardening/rotation features are present;
4. compiles the Rust core for ARM64 Android;
5. builds the Android APK;
6. verifies the APK signature;
7. uploads the APK and SHA-256 file as a GitHub Actions artifact.

### APK update safety

The current CI APK uses the GitHub runner's ephemeral Android debug certificate. A later CI APK can therefore have a different signing certificate and may **not install over an existing build**.

Do not uninstall a signer containing your only FROST share just to install a new CI APK. Back up and verify shares first. Until stable owner-controlled APK signing is configured, CI APKs are intended for a separate test profile/device rather than production in-place upgrades.

For that reason the workflow does not automatically publish each debug APK as a replacement GitHub Release asset.

## Share-format compatibility

The pinned Keep core exports encrypted shares as `kshare1...`.

Byte-for-byte compatibility with unrelated `bfshare1...` / `bfgroup1...` formats is not claimed. Glowstr interoperability uses NIP-46/NIP-55 and does not require Glowstr itself to parse FROST share backups.

## Security status

This is prototype/test signer software. The upstream code has substantial hardening and tests, and this overlay adds targeted UI/Android behavior, but this repository has not received an independent third-party security audit.

See `THIRD_PARTY_NOTICES.md` for upstream attribution.
