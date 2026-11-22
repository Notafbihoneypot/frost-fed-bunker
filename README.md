# Frost Fed Bunker

Android FROST threshold signer and NIP-46/NIP-55 signer for Glowstr/Nostr, built as small patches on pinned Keep Android and Keep Rust revisions.

The project intentionally reuses the upstream Rust FROST implementation instead of reimplementing threshold cryptography in Kotlin.

## Current 0.4.x base

- Keep Android: `09ca787c06257cc99e5574b14192a79e6117e088` (main, 2026-11-13, after v1.4.0)
- Keep Rust core: `e895a38c8f02ba711129bc224f70fbde27721723` (main, 2026-11-14, after v0.14.0)
- Android package: `org.glowstr.frostfedbunker`, version `0.4.1-frostr` (versionCode 12; ARM64 split 122)
- Toolchain: Rust 1.89.0 (upstream `rust-toolchain.toml`), NDK 29.0.14206865, JDK 21, compileSdk 37, Gradle 9.9.0, AGP 9.5.1

The Rust core is newer than the `keep.version` upstream Android pins (`794a2b2`). The two extra core commits only tighten NIP-55 relay-host parsing and recheck bunker FROST co-signatures; the UniFFI interface is unchanged.

Our changes live in `patches/keep-android.patch` (Kotlin UI/Android) and `patches/keep.patch` (Rust: `frost_refresh_exports` share rotation and its test, a relay-failure message that names each unreachable relay and why, and a `Cargo.lock` bump of the yanked `async-utility` 0.3.1 to 0.3.2).

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
- A bunker that cannot start says why, on the Bunker screen and in a notification (for example `wss://relay.example/: Timeout: TCP connect`), instead of silently stopping
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
- every export must carry an authenticated member list matching the supplied shares; older compact backups without one are refused, because their member count could be edited to silently drop a share;
- the core uses checked randomness for the refresh;
- each refreshed secret share is checked against its published verifying share before output;
- old and new shares must never be mixed.

The Android rotation screen accepts either one current export passphrase for every input share or one passphrase per line/share. The new passphrase must be at least 15 characters and not rated weak. After rotation, every refreshed share can be shown as QR and saved individually as a `.kshare` file.

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

FROST coordination relays and NIP-46 **Bunker Relays** are separate. Changing the Bunker Relay list while the bunker is running restarts the live bunker through the upstream start/retry state machine so the newly persisted list is actually used. Removing the final Bunker Relay disables/stops the bunker instead of allowing an old connection to keep serving silently.

The current upstream transport is relay/network based. A fully disconnected FROST signing flow would require a separate local/air-gap transport (for example LAN or multi-round animated QR); that is not claimed as implemented here.

## Android build

`./build-unsigned.sh` (used locally and by `.github/workflows/android.yml`):

1. fetches exactly the pinned Keep Android and Rust commits;
2. applies `patches/`, commits the patched core with a fixed date so `keep.version` and `SOURCE_DATE_EPOCH` are reproducible;
3. builds the Rust core for ARM64 with cargo-ndk and the `assembleRelease` APK;
4. refuses the output unless it is unsigned (no v1 entries, no APK Signing Block, `apksigner verify` fails), non-debuggable, has the expected package/version, and contains `lib/arm64-v8a/libkeep_mobile.so`;
5. writes `dist/Frost-Fed-Bunker-0.4.1-frostr-arm64-unsigned.apk` and its `.sha256`.

CI (`.github/workflows/android.yml`) runs the script on pushes to `frostr-0.4.0` and `claude/**` branches and on pull requests that touch the patches, then runs the patched Rust tests (share rotation and relay-failure message) and uploads `dist/` as the `Frost-Fed-Bunker-unsigned-release-arm64` artifact.

To change upstream pins: bump the SHAs in `build-unsigned.sh`, rebuild the patches against the new commits (`git apply --3way`, fix conflicts, `git diff`), and rerun the script.

### APK signing and update safety

Release APKs are **unsigned**; the owner signs them offline. See [OFFLINE-APK-SIGNING.md](OFFLINE-APK-SIGNING.md).

Earlier 0.3.x CI builds were signed with throwaway GitHub-runner debug keys. An owner-signed 0.4.0 cannot update over them. **Do not uninstall a signer holding your only FROST share**: export and verify every share first, then install the owner-signed build on a test profile/device.

## Save encrypted shares to files

Exporting and rotating shares happens in **Frost Fed Bunker**, not Glowstr.

- **Existing signer share:** Account → **Export encrypted FROST share backup**. Authenticate, choose a new export passphrase, and select **Save encrypted share to file** in the export result.
- **New offline identity:** Create Signing Group → Offline. After generating a 2-of-3 or 3-of-5 identity, choose **Save this encrypted share** under each QR code. Save each `.kshare` file, then tap **Next** and repeat for all shares.
- **Rotated shares:** Account → **Rotate FROST Shares**. After a successful full-set refresh, verify the unchanged group npub and use **Save this rotated share** for every replacement share.

These options use Android's system **Create Document** file picker and write only the FROST core's **passphrase-encrypted** share export. Choose a trusted offline destination rather than a cloud-syncing provider, separate storage locations for different shares, and verify recovery before deleting any original backup. Keep export passphrases separately.

**Never uninstall a signer with unique FROST shares merely to install a new build.** Uninstalling deletes its protected storage. Use a separate test profile until the owner-signed build is verified.

## Share-format compatibility

The pinned Keep core exports encrypted shares as `kshare1...`.

Byte-for-byte compatibility with unrelated `bfshare1...` / `bfgroup1...` formats is not claimed. Glowstr interoperability uses NIP-46/NIP-55 and does not require Glowstr itself to parse FROST share backups.

## Security status

This is prototype/test signer software. The upstream code has substantial hardening and tests, and this overlay adds targeted UI/Android behavior, but this repository has not received an independent third-party security audit.

See `THIRD_PARTY_NOTICES.md` for upstream attribution.
