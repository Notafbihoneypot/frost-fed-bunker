#!/usr/bin/env python3
# Frost Fed Bunker Android overlay.
"""Apply the minimal Frost bunker overlay to a pinned Keep Android checkout.

Every edit is anchored to an exact snippet of the pinned upstream sources and
must match exactly the expected number of times. All files are patched in
memory first and only written once every anchor has matched, so a pin bump
that moves an anchor fails loudly and leaves the checkout untouched instead of
producing a partially patched (and possibly less safe) app.
"""

from __future__ import annotations

import pathlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-overlay.py /path/to/keep-android")

root = pathlib.Path(sys.argv[1]).resolve()
if not (root / "app" / "build.gradle.kts").is_file():
    raise SystemExit(f"not a Keep Android checkout: {root}")

EXPECTED_KEEP = "d9192f5801949700dbefff2c9634b0fe904edf9e"
actual_keep = (root / "keep.version").read_text(encoding="utf-8").strip()
if actual_keep != EXPECTED_KEEP:
    raise SystemExit(f"unexpected keep.version: {actual_keep}; expected {EXPECTED_KEEP}")

UPSTREAM_ID = "io.privkey.keep"
APP_ID = "org.glowstr.igloomobile"
APP_NAME = "Frost bunker"

RES = ("app", "src", "main", "res", "values")
KOTLIN = ("app", "src", "main", "kotlin", "io", "privkey", "keep")


class Source:
    """One file of the checkout: read once, patched in memory, written once."""

    _pending: list["Source"] = []

    def __init__(self, *parts: str, create: bool = False) -> None:
        self.path = root.joinpath(*parts)
        if create:
            if self.path.exists():
                raise SystemExit(f"{self.path}: already exists; overlay applied twice?")
            self.text = ""
        else:
            self.text = self.path.read_text(encoding="utf-8")
        Source._pending.append(self)

    def replace(self, old: str, new: str, *, count: int = 1) -> None:
        found = self.text.count(old)
        if found != count:
            raise SystemExit(
                f"{self.path}: expected {count} match(es) for {old!r}, found {found}"
            )
        self.text = self.text.replace(old, new)

    def insert_before(self, anchor: str, addition: str) -> None:
        self.replace(anchor, addition + anchor)

    def insert_after(self, anchor: str, addition: str) -> None:
        self.replace(anchor, anchor + addition)

    @classmethod
    def save_all(cls) -> None:
        for source in cls._pending:
            source.path.write_text(source.text, encoding="utf-8")
        cls._pending.clear()


# --- Gradle: package identity, version, unsigned release, ARM64 only ---------

gradle = Source("app", "build.gradle.kts")
gradle.replace(f'applicationId = "{UPSTREAM_ID}"', f'applicationId = "{APP_ID}"')
gradle.replace('versionCode = 28', 'versionCode = 2')
gradle.replace('versionName = "1.2.0"', 'versionName = "0.1.1"')

# The pinned upstream signs release builds with the DEBUG key by default.
# For owner-held offline signing, release output MUST remain unsigned.
# Fail if upstream changes this anchor rather than silently leaking a test APK.
gradle.replace(
    '''            // findByName (not getByName) so the build still works when F-Droid
            // strips the "release" signing config: fall back to debug signing.
            val releaseConfig = signingConfigs.findByName("release")
            signingConfig = if (releaseConfig?.storeFile != null) {
                releaseConfig
            } else {
                signingConfigs.getByName("debug")
            }''',
    '''            // Owner signs unsigned release APK inside offline Qubes.
            signingConfig = null''',
)
gradle.replace('include("arm64-v8a", "x86_64")', 'include("arm64-v8a")')


# --- Branding strings --------------------------------------------------------

strings = Source(*RES, "strings.xml")
for key, upstream_value in (
    ("app_name", "Keep"),
    ("foreground_service_title", "Keep"),
    ("bunker_service_title", "Keep Bunker"),
    ("biometric_unlock_title", "Keep"),
):
    strings.replace(
        f'<string name="{key}" translatable="false">{upstream_value}</string>',
        f'<string name="{key}" translatable="false">{APP_NAME}</string>',
    )

main_strings = Source(*RES, "strings_main.xml")
for key, upstream_value, value in (
    ("main_unlock_title", "Unlock Keep", f"Unlock {APP_NAME}"),
    ("main_home_title", "Keep", APP_NAME),
    ("main_create_group_title", "Create Signing Group", "Create FROST Identity"),
    (
        "main_create_group_subtitle",
        "Authenticate to store share securely",
        "Create a threshold identity and store this device\\'s share securely",
    ),
    ("main_create_account_button", "Create Account", "Create single-key account (advanced)"),
):
    main_strings.replace(
        f'<string name="{key}">{upstream_value}</string>',
        f'<string name="{key}">{value}</string>',
    )

connections_strings = Source(*RES, "strings_connections.xml")
connections_strings.replace(
    '<string name="connections_bunker_rotate_url_button">Rotate Bunker URL</string>',
    '<string name="connections_bunker_rotate_url_button">Rotate NIP-46 connection keys</string>',
)

share_strings = Source(*RES, "strings_share.xml")
share_strings.insert_before(
    "</resources>",
    """
    <!-- Frost bunker advanced offline trusted-dealer setup -->
    <string name="igloo_offline_tab">Offline</string>
    <string name="igloo_offline_warning">Advanced setup: this phone temporarily generates the complete threshold key material and every share. Use an offline, trusted device. Distributed setup is safer because no single device ever holds the whole key.</string>
    <string name="igloo_offline_passphrase">Share export passphrase</string>
    <string name="igloo_offline_confirm_passphrase">Confirm passphrase</string>
    <string name="igloo_offline_acknowledge">I understand this device temporarily creates all shares and must be trusted during generation.</string>
    <string name="igloo_offline_generate">Generate encrypted shares offline</string>
    <string name="igloo_offline_recommendation">Recommended: keep this phone offline during generation, transfer each encrypted share to a different signer, verify the backups, then remove any exported share copies left on the generating device.</string>
    <string name="igloo_offline_generated_warning">Generation complete. Save every required share before leaving this screen. The same passphrase protects each exported share.</string>
    <string name="igloo_offline_share_position">Share %1$d of %2$d · FROST index %3$d</string>
    <string name="igloo_offline_share_qr">Encrypted FROST share %1$d</string>
    <string name="igloo_offline_transfer_hint">Scan this QR on the signer that should hold this share. Animated QR frames cycle automatically when the encrypted export is too large for one QR.</string>
    <string name="igloo_offline_previous">Previous share</string>
    <string name="igloo_offline_next">Next share</string>
    <string name="igloo_offline_finish">Clear generated shares from this screen</string>
""",
)


# --- Manifest and NIP-55 provider authorities --------------------------------

NIP55_AUTHORITIES = (
    "GET_PUBLIC_KEY",
    "SIGN_EVENT",
    "NIP04_ENCRYPT",
    "NIP04_DECRYPT",
    "NIP44_ENCRYPT",
    "NIP44_DECRYPT",
    "DECRYPT_ZAP_EVENT",
    "NIP44_V3_ENCRYPT",
    "NIP44_V3_DECRYPT",
)

manifest = Source("app", "src", "main", "AndroidManifest.xml")
manifest.replace(
    'android:authorities="' + ";".join(f"{UPSTREAM_ID}.{a}" for a in NIP55_AUTHORITIES) + '"',
    'android:authorities="' + ";".join(f"${{applicationId}}.{a}" for a in NIP55_AUTHORITIES) + '"',
)

# Register the private receiver behind the notification Reject action.
manifest.insert_before(
    '        <service\n            android:name=".nip46.BunkerService"',
    """
        <receiver
            android:name=".nip46.Nip46ApprovalActionReceiver"
            android:enabled="true"
            android:exported="false" />

""",
)

# The provider dispatches on uri.authority against hard-coded upstream
# authorities. The manifest above registers them under this app's package ID,
# so the constants must follow or every NIP-55 content-provider request is
# rejected as "unexpected authority".
nip55_provider = Source(*KOTLIN, "nip55", "Nip55ContentProvider.kt")
for authority in NIP55_AUTHORITIES:
    nip55_provider.replace(
        f'private const val AUTHORITY_{authority} = "{UPSTREAM_ID}.{authority}"',
        f'private const val AUTHORITY_{authority} = "{APP_ID}.{authority}"',
    )
nip55_provider.replace(f'uri.authority ?: "{UPSTREAM_ID}"', f'uri.authority ?: "{APP_ID}"')


# --- FROST identity screen: offline trusted-dealer setup and share refresh ---

create_group = Source(*KOTLIN, "CreateGroupScreen.kt")
create_group.insert_after(
    "import androidx.compose.ui.text.font.FontFamily\n",
    "import androidx.compose.ui.text.input.PasswordVisualTransformation\n"
    "import androidx.compose.foundation.text.KeyboardOptions\n"
    "import androidx.compose.ui.text.input.KeyboardType\n"
    "import io.privkey.keep.uniffi.FrostGenerationResult\n"
    "import io.privkey.keep.uniffi.KeepMobile\n"
    "import io.privkey.keep.uniffi.hexToNpub\n"
    "import kotlinx.coroutines.Dispatchers\n"
    "import kotlinx.coroutines.launch\n"
    "import kotlinx.coroutines.withContext\n"
    "import java.util.Arrays\n",
)
create_group.replace(
    """fun CreateGroupScreen(
    relays: List<String>,
""",
    """fun CreateGroupScreen(
    keepMobile: KeepMobile,
    relays: List<String>,
""",
)
create_group.replace(
    """    var isJoinMode by remember { mutableStateOf(false) }
""",
    """    var setupMode by remember { mutableStateOf(GroupSetupMode.DISTRIBUTED) }
""",
)
create_group.replace(
    """        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            SegmentedButton(
                selected = !isJoinMode,
                onClick = { isJoinMode = false },
                shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
            ) {
                Text(stringResource(R.string.create_group_mode_start))
            }
            SegmentedButton(
                selected = isJoinMode,
                onClick = { isJoinMode = true },
                shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
            ) {
                Text(stringResource(R.string.create_group_mode_join))
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        if (isJoinMode) {
            JoinGroupMode(onDkgBegin = onDkgBegin, runDkg = runDkg)
        } else {
            StartGroupMode(relays = relays, onDkgBegin = onDkgBegin, runDkg = runDkg)
        }
""",
    """        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            SegmentedButton(
                selected = setupMode == GroupSetupMode.DISTRIBUTED,
                onClick = { setupMode = GroupSetupMode.DISTRIBUTED },
                shape = SegmentedButtonDefaults.itemShape(index = 0, count = 3)
            ) {
                Text(stringResource(R.string.create_group_mode_start))
            }
            SegmentedButton(
                selected = setupMode == GroupSetupMode.JOIN,
                onClick = { setupMode = GroupSetupMode.JOIN },
                shape = SegmentedButtonDefaults.itemShape(index = 1, count = 3)
            ) {
                Text(stringResource(R.string.create_group_mode_join))
            }
            SegmentedButton(
                selected = setupMode == GroupSetupMode.OFFLINE,
                onClick = { setupMode = GroupSetupMode.OFFLINE },
                shape = SegmentedButtonDefaults.itemShape(index = 2, count = 3)
            ) {
                Text(stringResource(R.string.igloo_offline_tab))
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        when (setupMode) {
            GroupSetupMode.DISTRIBUTED ->
                StartGroupMode(relays = relays, onDkgBegin = onDkgBegin, runDkg = runDkg)
            GroupSetupMode.JOIN ->
                JoinGroupMode(onDkgBegin = onDkgBegin, runDkg = runDkg)
            GroupSetupMode.OFFLINE ->
                OfflineGroupMode(keepMobile = keepMobile)
        }
""",
)

# Make the common layouts obvious instead of hiding them behind +/- steppers.
create_group.replace(
    """            Spacer(modifier = Modifier.height(16.dp))

            Stepper(
                label = stringResource(R.string.create_group_threshold_label, threshold),
""",
    """            Spacer(modifier = Modifier.height(16.dp))

            ThresholdPresets(
                threshold = threshold,
                participants = participants,
                hint = "Pick a preset or use the controls below for a custom group."
            ) { presetThreshold, presetParticipants ->
                threshold = presetThreshold
                participants = presetParticipants
            }

            Spacer(modifier = Modifier.height(16.dp))

            Stepper(
                label = stringResource(R.string.create_group_threshold_label, threshold),
""",
)

create_group.insert_before(
    "private enum class CoordPhase { Form, Collect, Ready }\n",
    r'''

private fun splitNonBlankLines(value: String): List<String> =
    value.lines().map { it.trim() }.filter { it.isNotEmpty() }

private val THRESHOLD_PRESETS = listOf(2 to 3, 3 to 5)

@Composable
private fun ThresholdPresets(
    threshold: Int,
    participants: Int,
    hint: String,
    onSelect: (threshold: Int, participants: Int) -> Unit
) {
    Text(
        text = "Quick threshold presets",
        style = MaterialTheme.typography.titleSmall,
        modifier = Modifier.fillMaxWidth()
    )
    Spacer(modifier = Modifier.height(8.dp))
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        THRESHOLD_PRESETS.forEach { preset ->
            FilterChip(
                selected = threshold == preset.first && participants == preset.second,
                onClick = { onSelect(preset.first, preset.second) },
                label = { Text("${preset.first} of ${preset.second}") },
                modifier = Modifier.weight(1f)
            )
        }
    }
    Text(
        text = hint,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.fillMaxWidth()
    )
}

@Composable
private fun OfflineRefreshMode(
    keepMobile: KeepMobile,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var sharesText by remember { mutableStateOf("") }
    val oldPassphrase = remember { SecurePassphrase() }
    val newPassphrase = remember { SecurePassphrase() }
    val confirmPassphrase = remember { SecurePassphrase() }
    var oldPassphraseDisplay by remember { mutableStateOf("") }
    var newPassphraseDisplay by remember { mutableStateOf("") }
    var confirmPassphraseDisplay by remember { mutableStateOf("") }
    var rotating by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<FrostGenerationResult?>(null) }
    var selectedShare by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }

    // Keep the complete share set and its passphrases out of screenshots,
    // screen recordings and the recents thumbnail.
    DisposableEffect(Unit) {
        setSecureScreen(context, true)
        onDispose {
            setSecureScreen(context, false)
            oldPassphrase.clear()
            newPassphrase.clear()
            confirmPassphrase.clear()
            sharesText = ""
            result = null
        }
    }

    val refreshed = result
    if (refreshed != null) {
        val share = refreshed.shares[selectedShare]
        val frames by produceState<List<String>?>(initialValue = null, key1 = share.exportData) {
            value = withContext(Dispatchers.Default) {
                runCatching {
                    io.privkey.keep.uniffi.generateAnimatedFrames(share.exportData, 600u)
                }.getOrElse { listOf(share.exportData) }
            }
        }

        StatusCard(
            text = "FROST share rotation complete. The account npub is unchanged. Replace every old share with the matching new share; old and new shares must not be mixed.",
            containerColor = MaterialTheme.colorScheme.tertiaryContainer,
            contentColor = MaterialTheme.colorScheme.onTertiaryContainer
        )
        Spacer(modifier = Modifier.height(16.dp))
        val npub = remember(refreshed.groupPubkey) {
            hexToNpub(refreshed.groupPubkey) ?: refreshed.groupPubkey
        }
        NpubDisplay(npub)
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            "New share " + (selectedShare + 1) + " of " + refreshed.shares.size,
            style = MaterialTheme.typography.titleMedium
        )
        Spacer(modifier = Modifier.height(12.dp))

        val readyFrames = frames
        if (readyFrames == null) {
            CircularProgressIndicator()
        } else if (readyFrames.size > 1) {
            AnimatedQrCodeDisplay(
                frames = readyFrames,
                label = "Rotated FROST share " + share.shareIndex,
                fullData = share.exportData
            )
        } else {
            QrCodeDisplay(
                data = share.exportData,
                label = "Rotated FROST share " + share.shareIndex
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedButton(
                onClick = { if (selectedShare > 0) selectedShare-- },
                enabled = selectedShare > 0,
                modifier = Modifier.weight(1f)
            ) {
                Text("Previous")
            }
            Button(
                onClick = { if (selectedShare < refreshed.shares.lastIndex) selectedShare++ },
                enabled = selectedShare < refreshed.shares.lastIndex,
                modifier = Modifier.weight(1f)
            ) {
                Text("Next")
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        OutlinedButton(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Done")
        }
        return
    }

    StatusCard(
        text = "Offline share refresh keeps the same npub but replaces every FROST share. You must provide the COMPLETE current share set. Do this only on a trusted offline device.",
        containerColor = MaterialTheme.colorScheme.errorContainer,
        contentColor = MaterialTheme.colorScheme.onErrorContainer
    )
    Spacer(modifier = Modifier.height(16.dp))

    OutlinedTextField(
        value = sharesText,
        onValueChange = {
            sharesText = it
            error = null
        },
        label = { Text("Current encrypted shares (one kshare1... per line)") },
        // Share exports are not dictionary words: keep the keyboard from
        // autocorrecting them or learning them as suggestions.
        keyboardOptions = KeyboardOptions(
            autoCorrectEnabled = false,
            keyboardType = KeyboardType.Ascii
        ),
        modifier = Modifier.fillMaxWidth().heightIn(min = 160.dp),
        minLines = 5
    )

    Spacer(modifier = Modifier.height(12.dp))

    // KeyboardType.Password stops the IME from offering, learning or syncing
    // the passphrase as a typed word; the visual transformation alone only
    // hides it on screen.
    OutlinedTextField(
        value = oldPassphraseDisplay,
        onValueChange = {
            oldPassphrase.update(it)
            oldPassphraseDisplay = it
            error = null
        },
        label = { Text("Current share passphrase") },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth()
    )

    Spacer(modifier = Modifier.height(12.dp))

    OutlinedTextField(
        value = newPassphraseDisplay,
        onValueChange = {
            newPassphrase.update(it)
            newPassphraseDisplay = it
            error = null
        },
        label = { Text("New share passphrase") },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth()
    )

    Spacer(modifier = Modifier.height(12.dp))

    OutlinedTextField(
        value = confirmPassphraseDisplay,
        onValueChange = {
            confirmPassphrase.update(it)
            confirmPassphraseDisplay = it
            error = null
        },
        label = { Text("Confirm new passphrase") },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth()
    )

    error?.let {
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            it,
            color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodySmall
        )
    }

    Spacer(modifier = Modifier.height(16.dp))

    Button(
        onClick = {
            val shares = splitNonBlankLines(sharesText)
            when {
                shares.size < 2 -> error = "Provide the complete FROST share set"
                oldPassphrase.length == 0 -> error = "Current passphrase is required"
                newPassphrase.length < 15 -> error = "Use a new passphrase of at least 15 characters"
                !newPassphrase.contentEquals(confirmPassphrase) -> error = "New passphrases do not match"
                else -> {
                    val oldChars = oldPassphrase.toCharArray()
                    val newChars = newPassphrase.toCharArray()
                    rotating = true
                    scope.launch {
                        try {
                            val refreshedResult = withContext(Dispatchers.Default) {
                                keepMobile.frostRefreshExports(
                                    shares,
                                    List(shares.size) { String(oldChars) },
                                    "Refreshed FROST",
                                    String(newChars)
                                )
                            }
                            result = refreshedResult
                            selectedShare = 0
                            sharesText = ""
                            oldPassphrase.clear()
                            newPassphrase.clear()
                            confirmPassphrase.clear()
                            oldPassphraseDisplay = ""
                            newPassphraseDisplay = ""
                            confirmPassphraseDisplay = ""
                        } catch (e: Exception) {
                            if (BuildConfig.DEBUG) {
                                Log.e("OfflineFrost", "Share refresh failed: ${e::class.simpleName}")
                            }
                            error = "FROST share rotation failed. Verify that every current share and passphrase is correct."
                        } finally {
                            Arrays.fill(oldChars, '\u0000')
                            Arrays.fill(newChars, '\u0000')
                            rotating = false
                        }
                    }
                }
            }
        },
        enabled = !rotating,
        modifier = Modifier.fillMaxWidth()
    ) {
        if (rotating) {
            CircularProgressIndicator(
                modifier = Modifier.size(20.dp),
                strokeWidth = 2.dp
            )
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text("Rotate / refresh FROST shares")
    }

    Spacer(modifier = Modifier.height(8.dp))

    OutlinedButton(
        onClick = onBack,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text("Back")
    }
}


private enum class GroupSetupMode { DISTRIBUTED, JOIN, OFFLINE }

@Composable
private fun OfflineGroupMode(keepMobile: KeepMobile) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val passphrase = remember { SecurePassphrase() }
    val confirmPassphrase = remember { SecurePassphrase() }
    var passphraseDisplay by remember { mutableStateOf("") }
    var confirmPassphraseDisplay by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("Offline FROST") }
    var threshold by remember { mutableIntStateOf(2) }
    var participants by remember { mutableIntStateOf(3) }
    var acknowledged by remember { mutableStateOf(false) }
    var generating by remember { mutableStateOf(false) }
    var generationResult by remember { mutableStateOf<FrostGenerationResult?>(null) }
    var selectedShare by remember { mutableIntStateOf(0) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var refreshMode by remember { mutableStateOf(false) }

    if (refreshMode) {
        OfflineRefreshMode(keepMobile = keepMobile, onBack = { refreshMode = false })
        return
    }

    // Keep passphrase entry and every generated share out of screenshots,
    // screen recordings and the recents thumbnail.
    DisposableEffect(Unit) {
        setSecureScreen(context, true)
        onDispose {
            setSecureScreen(context, false)
            passphrase.clear()
            confirmPassphrase.clear()
            passphraseDisplay = ""
            confirmPassphraseDisplay = ""
            generationResult = null
        }
    }

    val generated = generationResult
    if (generated != null) {
        val share = generated.shares[selectedShare]
        val frames by produceState<List<String>?>(initialValue = null, key1 = share.exportData) {
            value = withContext(Dispatchers.Default) {
                runCatching {
                    io.privkey.keep.uniffi.generateAnimatedFrames(share.exportData, 600u)
                }.getOrElse { listOf(share.exportData) }
            }
        }

        StatusCard(
            text = stringResource(R.string.igloo_offline_generated_warning),
            containerColor = MaterialTheme.colorScheme.tertiaryContainer,
            contentColor = MaterialTheme.colorScheme.onTertiaryContainer
        )
        Spacer(modifier = Modifier.height(16.dp))

        val npub = remember(generated.groupPubkey) {
            hexToNpub(generated.groupPubkey) ?: generated.groupPubkey
        }
        NpubDisplay(npub)

        Spacer(modifier = Modifier.height(16.dp))
        Text(
            stringResource(
                R.string.igloo_offline_share_position,
                selectedShare + 1,
                generated.shares.size,
                share.shareIndex.toInt()
            ),
            style = MaterialTheme.typography.titleMedium
        )
        Spacer(modifier = Modifier.height(12.dp))

        val readyFrames = frames
        if (readyFrames == null) {
            CircularProgressIndicator()
        } else if (readyFrames.size > 1) {
            AnimatedQrCodeDisplay(
                frames = readyFrames,
                label = stringResource(R.string.igloo_offline_share_qr, share.shareIndex.toInt()),
                fullData = share.exportData
            )
        } else {
            QrCodeDisplay(
                data = share.exportData,
                label = stringResource(R.string.igloo_offline_share_qr, share.shareIndex.toInt())
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        Text(
            stringResource(R.string.igloo_offline_transfer_hint),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(16.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedButton(
                onClick = { if (selectedShare > 0) selectedShare-- },
                enabled = selectedShare > 0,
                modifier = Modifier.weight(1f)
            ) {
                Text(stringResource(R.string.igloo_offline_previous))
            }
            Button(
                onClick = {
                    if (selectedShare < generated.shares.lastIndex) selectedShare++
                },
                enabled = selectedShare < generated.shares.lastIndex,
                modifier = Modifier.weight(1f)
            ) {
                Text(stringResource(R.string.igloo_offline_next))
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        OutlinedButton(
            onClick = {
                generationResult = null
                selectedShare = 0
                acknowledged = false
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(stringResource(R.string.igloo_offline_finish))
        }
        return
    }

    OutlinedButton(
        onClick = { refreshMode = true },
        modifier = Modifier.fillMaxWidth()
    ) {
        Text("Rotate / refresh existing FROST shares")
    }
    Spacer(modifier = Modifier.height(16.dp))

    StatusCard(
        text = stringResource(R.string.igloo_offline_warning),
        containerColor = MaterialTheme.colorScheme.errorContainer,
        contentColor = MaterialTheme.colorScheme.onErrorContainer
    )
    Spacer(modifier = Modifier.height(16.dp))

    OutlinedTextField(
        value = name,
        onValueChange = { if (it.length <= MAX_ACCOUNT_NAME_LENGTH) name = it },
        label = { Text(stringResource(R.string.create_group_name_label)) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true
    )

    Spacer(modifier = Modifier.height(16.dp))

    ThresholdPresets(
        threshold = threshold,
        participants = participants,
        hint = "Offline mode will generate all selected shares on this device so you can distribute them afterward."
    ) { presetThreshold, presetParticipants ->
        threshold = presetThreshold
        participants = presetParticipants
    }

    Spacer(modifier = Modifier.height(16.dp))

    Stepper(
        label = stringResource(R.string.create_group_threshold_label, threshold),
        decrementDescription = stringResource(R.string.create_group_threshold_decrement),
        incrementDescription = stringResource(R.string.create_group_threshold_increment),
        onDecrement = { if (threshold > 2) threshold-- },
        onIncrement = { if (threshold < participants) threshold++ },
        canDecrement = threshold > 2,
        canIncrement = threshold < participants
    )

    Spacer(modifier = Modifier.height(8.dp))

    Stepper(
        label = stringResource(R.string.create_group_participants_label, participants),
        decrementDescription = stringResource(R.string.create_group_participants_decrement),
        incrementDescription = stringResource(R.string.create_group_participants_increment),
        onDecrement = {
            if (participants > 2) {
                participants--
                if (threshold > participants) threshold = participants
            }
        },
        onIncrement = { if (participants < MAX_PARTICIPANTS) participants++ },
        canDecrement = participants > 2,
        canIncrement = participants < MAX_PARTICIPANTS
    )

    Spacer(modifier = Modifier.height(16.dp))

    OutlinedTextField(
        value = passphraseDisplay,
        onValueChange = {
            passphrase.update(it)
            passphraseDisplay = it
            errorMessage = null
        },
        label = { Text(stringResource(R.string.igloo_offline_passphrase)) },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth()
    )

    Spacer(modifier = Modifier.height(12.dp))

    OutlinedTextField(
        value = confirmPassphraseDisplay,
        onValueChange = {
            confirmPassphrase.update(it)
            confirmPassphraseDisplay = it
            errorMessage = null
        },
        label = { Text(stringResource(R.string.igloo_offline_confirm_passphrase)) },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
        isError = confirmPassphrase.length > 0 && !passphrase.contentEquals(confirmPassphrase)
    )

    Spacer(modifier = Modifier.height(12.dp))

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()
    ) {
        Checkbox(
            checked = acknowledged,
            onCheckedChange = { acknowledged = it }
        )
        Text(
            stringResource(R.string.igloo_offline_acknowledge),
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.weight(1f)
        )
    }

    if (errorMessage != null) {
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            errorMessage!!,
            color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodySmall
        )
    }

    Spacer(modifier = Modifier.height(16.dp))

    Button(
        onClick = {
            when {
                name.isBlank() -> errorMessage = "Name is required"
                passphrase.length < 15 -> errorMessage = "Use a passphrase of at least 15 characters"
                !passphrase.contentEquals(confirmPassphrase) -> errorMessage = "Passphrases do not match"
                !acknowledged -> errorMessage = "Confirm the offline-generation warning first"
                else -> {
                    val passphraseChars = passphrase.toCharArray()
                    generating = true
                    errorMessage = null
                    scope.launch {
                        try {
                            val result = withContext(Dispatchers.Default) {
                                keepMobile.frostGenerate(
                                    threshold.toUShort(),
                                    participants.toUShort(),
                                    name.trim(),
                                    String(passphraseChars)
                                )
                            }
                            generationResult = result
                            selectedShare = 0
                            passphrase.clear()
                            confirmPassphrase.clear()
                            passphraseDisplay = ""
                            confirmPassphraseDisplay = ""
                        } catch (e: Exception) {
                            if (BuildConfig.DEBUG) {
                                Log.e("OfflineFrost", "Trusted-dealer generation failed: ${e::class.simpleName}")
                            }
                            errorMessage = "Offline share generation failed"
                        } finally {
                            Arrays.fill(passphraseChars, '\u0000')
                            generating = false
                        }
                    }
                }
            }
        },
        enabled = !generating,
        modifier = Modifier.fillMaxWidth()
    ) {
        if (generating) {
            CircularProgressIndicator(
                modifier = Modifier.size(20.dp),
                strokeWidth = 2.dp
            )
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(stringResource(R.string.igloo_offline_generate))
    }

    Spacer(modifier = Modifier.height(8.dp))
    Text(
        stringResource(R.string.igloo_offline_recommendation),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

''',
)


# --- MainActivity: pass KeepMobile through, request notification permission --

main_activity = Source(*KOTLIN, "MainActivity.kt")
main_activity.replace(
    """        CreateGroupScreen(
            relays = groupRelays,
""",
    """        CreateGroupScreen(
            keepMobile = keepMobile,
            relays = groupRelays,
""",
)

# Android 13+ notification permission. The manifest declares the permission,
# but modern Android requires a runtime prompt before approval notifications
# can appear.
main_activity.replace(
    "import android.content.Context\n",
    "import android.Manifest\n"
    "import android.content.Context\n"
    "import android.content.pm.PackageManager\n"
    "import android.os.Build\n",
)
main_activity.insert_after(
    "import androidx.fragment.app.FragmentActivity\n",
    "import androidx.core.content.ContextCompat\n",
)
main_activity.replace(
    """        super.onCreate(savedInstanceState)

        val app = application as? KeepMobileApp ?: run { finish(); return }
""",
    """        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                4601
            )
        }

        val app = application as? KeepMobileApp ?: run { finish(); return }
""",
)


# --- BunkerService: hardened foreground start, Amber-style approvals ---------

bunker_service = Source(*KOTLIN, "nip46", "BunkerService.kt")

# A failed notification or FGS promotion should set an error state instead of
# taking down the whole process.
bunker_service.replace(
    """        startForeground(NOTIFICATION_ID, createNotification(isActive = false))
""",
    """        try {
            startForeground(NOTIFICATION_ID, createNotification(isActive = false))
        } catch (e: Exception) {
            if (BuildConfig.DEBUG) Log.e(TAG, "Unable to enter foreground mode", e)
            _status.value = BunkerStatus.ERROR
            stopSelf()
            return START_NOT_STICKY
        }
""",
)
bunker_service.replace(
    """    private fun updateNotification(isActive: Boolean) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, createNotification(isActive))
    }
""",
    """    private fun updateNotification(isActive: Boolean) {
        val manager = getSystemService(NotificationManager::class.java)
        runCatching {
            manager.notify(NOTIFICATION_ID, createNotification(isActive))
        }.onFailure {
            if (BuildConfig.DEBUG) Log.e(TAG, "Failed to update bunker notification", it)
        }
    }
""",
)

# NIP-46 signing approvals arrive as a normal high-priority notification with
# inline Approve/Reject actions. Do not force-launch an activity from the
# background; tapping the notification still opens the detailed approval screen.
bunker_service.replace(
    """        runCatching { startActivity(intent) }
        postApprovalNotification(requestId, request, intent)
""",
    """        postApprovalNotification(requestId, request, intent)
""",
)
bunker_service.insert_before(
    """        val appLabel = sanitizeDisplayName(request.appName).ifBlank { truncatePubkey(request.appPubkey) }
        val body = getString(R.string.bunker_approval_notification_text, appLabel, sanitizeDisplayName(request.method))
""",
    """        // Approval must still pass through Nip46ApprovalActivity so the
        // biometric/Keystore gate cannot be bypassed from a notification action.
        val approveIntent = contentIntent
        val rejectIntent = PendingIntent.getBroadcast(
            this,
            notificationId * 2 + 2,
            Intent(this, Nip46ApprovalActionReceiver::class.java)
                .setAction(Nip46ApprovalActionReceiver.ACTION_REJECT)
                .putExtra(Nip46ApprovalActionReceiver.EXTRA_REQUEST_ID, requestId),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
""",
)
# Also drops the alarm/call-style full-screen intent.
bunker_service.replace(
    """            .setContentIntent(contentIntent)
            .setFullScreenIntent(contentIntent, true)
            .setAutoCancel(true)
""",
    """            .setContentIntent(contentIntent)
            .addAction(
                R.drawable.ic_notification,
                getString(R.string.cosign_approve),
                approveIntent
            )
            .addAction(
                R.drawable.ic_notification,
                getString(R.string.cosign_reject),
                rejectIntent
            )
            .setAutoCancel(true)
""",
)

approval_receiver = Source(*KOTLIN, "nip46", "Nip46ApprovalActionReceiver.kt", create=True)
approval_receiver.text = f'''package io.privkey.keep.nip46

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class Nip46ApprovalActionReceiver : BroadcastReceiver() {{
    override fun onReceive(context: Context, intent: Intent) {{
        val requestId = intent.getStringExtra(EXTRA_REQUEST_ID) ?: return
        if (intent.action == ACTION_REJECT) {{
            BunkerService.respondToApproval(requestId, false)
        }}
    }}

    companion object {{
        const val ACTION_REJECT = "{APP_ID}.NIP46_REJECT"
        const val EXTRA_REQUEST_ID = "nip46_approval_request_id"
    }}
}}
'''


# --- Crash capture: persist the last uncaught exception for diagnostics ------

keep_app = Source(*KOTLIN, "KeepMobileApp.kt")
keep_app.replace(
    """    override fun onCreate() {
        super.onCreate()
        initializeKeepMobile()
""",
    """    override fun onCreate() {
        super.onCreate()
        installCrashCapture()
        initializeKeepMobile()
""",
)
keep_app.insert_before(
    """    private fun initializeKeepMobile() {
""",
    r'''    private fun installCrashCapture() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            runCatching {
                // Exception messages can embed user data (relay URLs, event
                // content, fragments of a share or key in a parse error), and
                // this report is written unencrypted and later shared through
                // the diagnostics export. Persist only exception class names
                // and stack frames, bounded in depth and length.
                val report = buildString {
                    appendLine("timestamp=" + java.time.Instant.now().toString())
                    appendLine("thread=" + thread.name)
                    var current: Throwable? = throwable
                    var depth = 0
                    while (current != null && depth < 8) {
                        appendLine((if (depth == 0) "exception=" else "caused_by=") + current.javaClass.name)
                        for (frame in current.stackTrace.take(64)) {
                            appendLine("    at $frame")
                        }
                        current = current.cause
                        depth++
                    }
                }
                java.io.File(filesDir, "last_crash.txt").writeText(report, Charsets.UTF_8)
            }
            if (previous != null) {
                previous.uncaughtException(thread, throwable)
            } else {
                android.os.Process.killProcess(android.os.Process.myPid())
                kotlin.system.exitProcess(10)
            }
        }
    }

''',
)

export_logs = Source(*KOTLIN, "ExportLogsScreen.kt")
export_logs.insert_after(
    "import android.content.ActivityNotFoundException\n",
    "import android.content.Context\n",
)
export_logs.replace(
    """                    buildExportContent(
                        keepMobile = keepMobile,
""",
    """                    buildExportContent(
                        context = context,
                        keepMobile = keepMobile,
""",
)
export_logs.replace(
    """private suspend fun buildExportContent(
    keepMobile: KeepMobile,
""",
    """private suspend fun buildExportContent(
    context: Context,
    keepMobile: KeepMobile,
""",
)
export_logs.insert_before(
    """    return buildString {
        appendLine("=== Keep Diagnostics ===")
""",
    r'''    val lastCrash = runCatching {
        File(context.filesDir, "last_crash.txt")
            .takeIf { it.isFile }
            ?.readText(Charsets.UTF_8)
            ?.take(100_000)
    }.getOrNull()

''',
)
export_logs.insert_after(
    """        if (activityLogResult == null) {
            appendLine("(unavailable)")
        } else {
            val (text, exported, total) = activityLogResult
            if (total > exported) {
                appendLine("(truncated to $exported of $total entries)")
            }
            if (text.isBlank()) appendLine("(no activity)") else appendLine(text)
        }
""",
    r'''        appendLine()
        appendLine("=== Last Uncaught Crash ===")
        if (lastCrash.isNullOrBlank()) {
            appendLine("(none captured)")
        } else {
            appendLine(lastCrash)
        }
''',
)


# --- Rust core: expose proactive FROST share refresh to Android --------------
#
# This requires the COMPLETE current share set and preserves the group public
# key/npub while replacing all signing shares. It is intentionally an offline
# trusted-device operation.

keep_mobile_rs = Source("keep", "keep-mobile", "src", "lib.rs")
keep_mobile_rs.insert_before(
    """    /// FFI split, option B (§8): mint (or re-mint) this device's per-group DKG
""",
    r'''    /// Refresh an existing complete FROST share set offline.
    ///
    /// This is proactive share rotation: the group public key stays the same,
    /// while every signing share changes. The full current share set is required
    /// so no absent participant is silently orphaned.
    pub fn frost_refresh_exports(
        &self,
        share_data: Vec<String>,
        passphrases: Vec<String>,
        name: String,
        new_passphrase: String,
    ) -> Result<FrostGenerationResult, KeepMobileError> {
        let share_data: Vec<Zeroizing<String>> =
            share_data.into_iter().map(Zeroizing::new).collect();
        let passphrases: Vec<Zeroizing<String>> =
            passphrases.into_iter().map(Zeroizing::new).collect();
        let new_passphrase = Zeroizing::new(new_passphrase);

        Self::validate_share_name(&name)?;
        if share_data.is_empty() || share_data.len() != passphrases.len() {
            return Err(KeepMobileError::InvalidShare {
                msg: "Provide every share and one passphrase per share".into(),
            });
        }

        let mut exports = Vec::with_capacity(share_data.len());
        for data in &share_data {
            let export = ShareExport::parse(data.as_str())
                .map_err(|e| KeepMobileError::InvalidShare { msg: e.to_string() })?;
            if export.ciphersuite != keep_core::frost::Ciphersuite::Secp256k1Tr {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Only secp256k1 (Bitcoin/Nostr) shares are supported".into(),
                });
            }
            exports.push(export);
        }

        // Reject an incomplete, mixed or duplicated set from the cleartext
        // export headers before decrypting anything: every decryption below
        // costs a full Argon2id derivation (256 MiB, several seconds on a
        // phone). The headers are not trusted; the same invariants are
        // re-checked on the decrypted shares.
        let first_export = exports.first().ok_or_else(|| KeepMobileError::InvalidShare {
            msg: "No shares supplied".into(),
        })?;
        if exports.len() != first_export.total as usize {
            return Err(KeepMobileError::InvalidShare {
                msg: format!(
                    "Share refresh requires the full set of {} shares; got {}",
                    first_export.total,
                    exports.len()
                ),
            });
        }
        let mut export_identifiers = std::collections::HashSet::new();
        for export in &exports {
            if !export
                .group_pubkey
                .eq_ignore_ascii_case(&first_export.group_pubkey)
                || export.threshold != first_export.threshold
                || export.total != first_export.total
            {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Shares do not belong to the same FROST group".into(),
                });
            }
            if !export_identifiers.insert(export.identifier) {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Duplicate FROST share identifier".into(),
                });
            }
        }

        let mut shares = Vec::with_capacity(exports.len());
        for (export, passphrase) in exports.iter().zip(passphrases.iter()) {
            let share = export
                .to_share(passphrase, &name)
                .map_err(|e| KeepMobileError::InvalidShare { msg: e.to_string() })?;
            shares.push(share);
        }

        let first = shares.first().ok_or_else(|| KeepMobileError::InvalidShare {
            msg: "No shares supplied".into(),
        })?;
        let total = first.metadata.total_shares as usize;
        if shares.len() != total {
            return Err(KeepMobileError::InvalidShare {
                msg: format!(
                    "Share refresh requires the full set of {total} shares; got {}",
                    shares.len()
                ),
            });
        }

        let group_pubkey = first.metadata.group_pubkey;
        let threshold = first.metadata.threshold;
        let mut identifiers = std::collections::HashSet::new();
        for share in &shares {
            if share.metadata.group_pubkey != group_pubkey
                || share.metadata.threshold != threshold
                || share.metadata.total_shares as usize != total
            {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Shares do not belong to the same FROST group".into(),
                });
            }
            if !identifiers.insert(share.metadata.identifier) {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Duplicate FROST share identifier".into(),
                });
            }
        }

        let (refreshed, _) = keep_core::frost::refresh_shares(&shares)
            .map_err(|e| KeepMobileError::FrostError { msg: e.to_string() })?;

        if refreshed.iter().any(|s| s.metadata.group_pubkey != group_pubkey) {
            return Err(KeepMobileError::FrostError {
                msg: "Group public key changed during refresh; refusing output".into(),
            });
        }

        Self::build_generation_result(&refreshed, &new_passphrase)
    }

''',
)


Source.save_all()
print("Frost bunker overlay applied successfully")
