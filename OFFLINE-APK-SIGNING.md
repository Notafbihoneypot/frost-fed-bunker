# Frost Fed Bunker — owner-controlled offline Android signing

Android package ID: org.glowstr.frostfedbunker (same as the 0.3.x test builds)
Launcher name: Frost Fed Bunker
Planned owner-signed release: 0.4.0-frostr (base versionCode 11; ARM64 split versionCode 112).

**Never give CI, GitHub, a VPS, or another online device the offline Qubes signing key or keystore password.**

## WARNING — export/restore FROST shares BEFORE changing packages

A release signed with your new key generally **cannot update** a test APK signed with a different CI/debug key. On Android, the same package ID + unrelated certificate usually yields INSTALL_FAILED_UPDATE_INCOMPATIBLE. An old signing private key is required to authorize a genuine signing lineage/rotation, and an ephemeral CI debug key may be lost.

**Do not uninstall the existing Frost Fed Bunker** until you have:
1. Encrypted export of every share controlled by that device (or complete, tested distributed-signing recovery plan).
2. Passwords to decrypt those exports. Verify a test import on a separate trusted device/profile, where possible.
3. Group public key / npub, signing threshold, roster, bunker URL, relay URLs, and NIP-46 client re-pairing plan.
4. Verified backup of any standalone nsec, if one is used. Never assume Android Keystore secrets can survive uninstall.

FROST shares are cryptographic signing authority; losing enough shares can permanently lock you out of the group identity. Merely having the npub is insufficient. Do not publish share QR exports, passphrases, seeds or private keys.

## 1. Build unsigned

Run `./build-unsigned.sh`, or GitHub -> Actions -> Build Frost Fed Bunker Android (unsigned release). From CI download the artifact named Frost-Fed-Bunker-unsigned-release-arm64:
- Frost-Fed-Bunker-0.4.0-frostr-arm64-unsigned.apk
- Frost-Fed-Bunker-0.4.0-frostr-arm64-unsigned.apk.sha256

The patches remove upstream Keep Android's fallback to signing release builds with a debug certificate. The build fails if the supposed unsigned APK is signed or debuggable.

On the downloading machine:
~~~sh
sha256sum -c Frost-Fed-Bunker-0.4.0-frostr-arm64-unsigned.apk.sha256
~~~

Transfer only those two files to the network-disabled signing qube and recheck SHA-256 there.

## 2. Offline signing with your existing key

Preinstall trusted JDK + Android SDK Build Tools (apksigner, zipalign, aapt) inside the offline signing qube without exposing the key to the network. Use a **distinct Frost Fed Bunker signing keypair**, separate from Glowstr's signer if possible.

Verify public certificate details before signing:
~~~sh
keytool -list -v -keystore /offline/keys/frost-bunker-release.jks
~~~

Sign in the offline qube (edit path and alias to match your existing key):
~~~sh
umask 077
cd /path/to/unsigned-frost-apk
sha256sum -c Frost-Fed-Bunker-0.4.0-frostr-arm64-unsigned.apk.sha256

zipalign -P 16 -f -v 4 Frost-Fed-Bunker-0.4.0-frostr-arm64-unsigned.apk Frost-Fed-Bunker-0.4.0-frostr-aligned.apk

apksigner sign \
  --ks /offline/keys/frost-bunker-release.jks \
  --ks-key-alias MY_FROST_ALIAS \
  --out Frost-Fed-Bunker-0.4.0-frostr.apk \
  Frost-Fed-Bunker-0.4.0-frostr-aligned.apk

apksigner verify --verbose --print-certs Frost-Fed-Bunker-0.4.0-frostr.apk
zipalign -c -P 16 -v 4 Frost-Fed-Bunker-0.4.0-frostr.apk
aapt dump badging Frost-Fed-Bunker-0.4.0-frostr.apk | head -5
sha256sum Frost-Fed-Bunker-0.4.0-frostr.apk > Frost-Fed-Bunker-0.4.0-frostr.apk.sha256
~~~

The expected package ID is org.glowstr.frostfedbunker, and app label is Frost Fed Bunker. The ARM64 split APK must target aarch64/arm64-v8a; it will not install on x86-only Android devices. Confirm the reported signer SHA-256 matches the public key fingerprint from keytool.

## 3. Migration and rollout

Return only the signed APK and checksum to an online publishing qube. The private key never leaves offline Qubes. Publish signed artifacts with the exact source commit, build-tool versions, versionCode, and public signer fingerprint.

**On a sacrificial test device first**, confirm import of encrypted shares, signer unlock/biometrics, NIP-46 approvals/rejections, cancellation/back navigation, notification actions, bunker relay reconnection, share QR export/import, and FROST refresh with a **test identity**, not real signing shares.

Use adb install -r Frost-Fed-Bunker-0.4.0-frostr.apk only when you expect the package ID and signing identity to match. An incompatible existing test APK must be uninstalled AFTER tested recovery; new key cannot automatically replace old key.

Every future update must have a higher versionCode than the installed one, retain org.glowstr.frostfedbunker, and use the same offline Frost signing key. Keep two geographically separated encrypted backups and recovery procedure. Never attach a signer private key or keystore to GitHub.

## 4. Key rotation

Android APK signer rotation is DIFFERENT from FROST SHARE ROTATION. The former is authorization of a new APK signing certificate by the old APK signing private key; the latter changes threshold shares (and may preserve the Nostr group npub). Neither can substitute for the other.

Android 13+ supports enhanced v3.1 signing lineage; rotation requires both old and new signer keys, not just the two public certificates. Follow official apksigner instructions and test API compatibility before trying it on existing installs:
https://developer.android.com/tools/apksigner
https://source.android.com/docs/security/features/apksigning/v3-1
