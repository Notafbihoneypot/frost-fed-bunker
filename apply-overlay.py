#!/usr/bin/env python3
# Frost Fed Bunker Android overlay.
"""Apply the Frost Fed Bunker FROSTR overlay to a pinned Keep Android checkout."""

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


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match for {old!r}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


gradle = root / "app" / "build.gradle.kts"
replace_once(gradle, 'applicationId = "io.privkey.keep"', 'applicationId = "org.glowstr.frostfedbunker"')
replace_once(gradle, 'versionCode = 28', 'versionCode = 6')
replace_once(gradle, 'versionName = "1.2.0"', 'versionName = "0.2.4-frostr"')
replace_once(
    gradle,
    'include("arm64-v8a", "x86_64")',
    'include("arm64-v8a")',
)

strings = root / "app" / "src" / "main" / "res" / "values" / "strings.xml"
replace_once(
    strings,
    '<string name="app_name" translatable="false">Keep</string>',
    '<string name="app_name" translatable="false">Frost Fed Bunker</string>',
)
replace_once(
    strings,
    '<string name="foreground_service_title" translatable="false">Keep</string>',
    '<string name="foreground_service_title" translatable="false">Frost Fed Bunker</string>',
)
replace_once(
    strings,
    '<string name="bunker_service_title" translatable="false">Keep Bunker</string>',
    '<string name="bunker_service_title" translatable="false">Frost Fed Bunker Signer</string>',
)
replace_once(
    strings,
    '<string name="biometric_unlock_title" translatable="false">Keep</string>',
    '<string name="biometric_unlock_title" translatable="false">Frost Fed Bunker</string>',
)

main_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_main.xml"
replace_once(
    main_strings,
    '<string name="main_unlock_title">Unlock Keep</string>',
    '<string name="main_unlock_title">Unlock Frost Fed Bunker</string>',
)
replace_once(
    main_strings,
    '<string name="main_home_title">Keep</string>',
    '<string name="main_home_title">Frost Fed Bunker</string>',
)
replace_once(
    main_strings,
    '<string name="main_create_group_title">Create Signing Group</string>',
    '<string name="main_create_group_title">Create FROST Identity</string>',
)
replace_once(
    main_strings,
    '<string name="main_create_group_subtitle">Authenticate to store share securely</string>',
    '<string name="main_create_group_subtitle">Create a threshold identity and store this device\\\'s share securely</string>',
)
replace_once(
    main_strings,
    '<string name="main_create_account_button">Create Account</string>',
    '<string name="main_create_account_button">Create single-key account (advanced)</string>',
)

ms = main_strings.read_text(encoding="utf-8")
ms = ms.replace(
    '<string name="main_export_share_button">Export Share</string>',
    '<string name="main_export_share_button">Export encrypted FROST share backup</string>',
    1,
)
ms = ms.replace(
    '<string name="main_keys_title">Keys</string>',
    '<string name="main_keys_title">FROST Shares</string>',
    1,
)
main_strings.write_text(ms, encoding="utf-8")

manifest = root / "app" / "src" / "main" / "AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")
old = 'android:authorities="io.privkey.keep.GET_PUBLIC_KEY;io.privkey.keep.SIGN_EVENT;io.privkey.keep.NIP04_ENCRYPT;io.privkey.keep.NIP04_DECRYPT;io.privkey.keep.NIP44_ENCRYPT;io.privkey.keep.NIP44_DECRYPT;io.privkey.keep.DECRYPT_ZAP_EVENT;io.privkey.keep.NIP44_V3_ENCRYPT;io.privkey.keep.NIP44_V3_DECRYPT"'
new = 'android:authorities="${applicationId}.GET_PUBLIC_KEY;${applicationId}.SIGN_EVENT;${applicationId}.NIP04_ENCRYPT;${applicationId}.NIP04_DECRYPT;${applicationId}.NIP44_ENCRYPT;${applicationId}.NIP44_DECRYPT;${applicationId}.DECRYPT_ZAP_EVENT;${applicationId}.NIP44_V3_ENCRYPT;${applicationId}.NIP44_V3_DECRYPT"'
if text.count(old) != 1:
    raise SystemExit("AndroidManifest.xml: unexpected NIP-55 provider authorities")
manifest.write_text(text.replace(old, new, 1), encoding="utf-8")


# Add the advanced offline trusted-dealer setup to the FROST identity screen.
create_group = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "CreateGroupScreen.kt"
cg = create_group.read_text(encoding="utf-8")

cg = cg.replace(
    "import androidx.compose.ui.text.font.FontFamily\n",
    "import androidx.compose.ui.text.font.FontFamily\n"
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
    1,
)

old_sig = """fun CreateGroupScreen(
    relays: List<String>,
"""
new_sig = """fun CreateGroupScreen(
    keepMobile: KeepMobile,
    relays: List<String>,
"""
if old_sig not in cg:
    raise SystemExit("CreateGroupScreen signature not found")
cg = cg.replace(old_sig, new_sig, 1)

old_mode = """    var isJoinMode by remember { mutableStateOf(false) }
"""
new_mode = """    var setupMode by remember { mutableStateOf(GroupSetupMode.DISTRIBUTED) }
"""
if old_mode not in cg:
    raise SystemExit("CreateGroupScreen mode state not found")
cg = cg.replace(old_mode, new_mode, 1)

old_tabs = """        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
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
"""
new_tabs = """        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
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
"""
if old_tabs not in cg:
    raise SystemExit("CreateGroupScreen tabs block not found")
cg = cg.replace(old_tabs, new_tabs, 1)

offline_code = r'''

private fun splitNonBlankLines(value: String): List<String> =
    value.lines().map { it.trim() }.filter { it.isNotEmpty() }

@Composable
private fun OfflineRefreshMode(
    keepMobile: KeepMobile,
    onBack: () -> Unit
) {
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

    DisposableEffect(Unit) {
        onDispose {
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
        NpubDisplay(hexToNpub(refreshed.groupPubkey) ?: refreshed.groupPubkey)
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
        modifier = Modifier.fillMaxWidth().heightIn(min = 160.dp),
        minLines = 5
    )

    Spacer(modifier = Modifier.height(12.dp))

    OutlinedTextField(
        value = oldPassphraseDisplay,
        onValueChange = {
            oldPassphrase.update(it)
            oldPassphraseDisplay = it
            error = null
        },
        label = { Text("Current share passphrase") },
        visualTransformation = PasswordVisualTransformation(),
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
                                Log.e("OfflineFrost", "Share refresh failed", e)
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

    DisposableEffect(Unit) {
        onDispose {
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
        onIncrement = { if (participants < 8) participants++ },
        canDecrement = participants > 2,
        canIncrement = participants < 8
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
                                Log.e("OfflineFrost", "Trusted-dealer generation failed: \${e::class.simpleName}")
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

'''
marker = "private enum class CoordPhase { Form, Collect, Ready }\n"
if marker not in cg:
    raise SystemExit("CoordPhase marker not found")
cg = cg.replace(marker, offline_code + marker, 1)

# FROSTFED_THRESHOLD_PRESETS
# Make the common layouts obvious instead of hiding them behind +/- steppers.
preset_anchor = """            Spacer(modifier = Modifier.height(16.dp))

            Stepper(
                label = stringResource(R.string.create_group_threshold_label, threshold),
"""
preset_block = """            Spacer(modifier = Modifier.height(16.dp))

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
                FilterChip(
                    selected = threshold == 2 && participants == 3,
                    onClick = {
                        threshold = 2
                        participants = 3
                    },
                    label = { Text("2 of 3") },
                    modifier = Modifier.weight(1f)
                )
                FilterChip(
                    selected = threshold == 3 && participants == 5,
                    onClick = {
                        threshold = 3
                        participants = 5
                    },
                    label = { Text("3 of 5") },
                    modifier = Modifier.weight(1f)
                )
            }
            Text(
                text = "Pick a preset or use the controls below for a custom group.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(16.dp))

            Stepper(
                label = stringResource(R.string.create_group_threshold_label, threshold),
"""
if preset_anchor not in cg:
    raise SystemExit("distributed threshold preset anchor not found")
cg = cg.replace(preset_anchor, preset_block, 1)

offline_preset_anchor = """    Spacer(modifier = Modifier.height(16.dp))

    Stepper(
        label = stringResource(R.string.create_group_threshold_label, threshold),
"""
offline_preset_block = """    Spacer(modifier = Modifier.height(16.dp))

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
        FilterChip(
            selected = threshold == 2 && participants == 3,
            onClick = {
                threshold = 2
                participants = 3
            },
            label = { Text("2 of 3") },
            modifier = Modifier.weight(1f)
        )
        FilterChip(
            selected = threshold == 3 && participants == 5,
            onClick = {
                threshold = 3
                participants = 5
            },
            label = { Text("3 of 5") },
            modifier = Modifier.weight(1f)
        )
    }
    Text(
        text = "Offline mode will generate all selected shares on this device so you can distribute them afterward.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.fillMaxWidth()
    )

    Spacer(modifier = Modifier.height(16.dp))

    Stepper(
        label = stringResource(R.string.create_group_threshold_label, threshold),
"""
if offline_preset_anchor not in cg:
    raise SystemExit("offline threshold preset anchor not found")
cg = cg.replace(offline_preset_anchor, offline_preset_block, 1)

create_group.write_text(cg, encoding="utf-8")

main_activity = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "MainActivity.kt"
ma = main_activity.read_text(encoding="utf-8")
old_call = """        CreateGroupScreen(
            relays = groupRelays,
"""
new_call = """        CreateGroupScreen(
            keepMobile = keepMobile,
            relays = groupRelays,
"""
if old_call not in ma:
    raise SystemExit("MainActivity CreateGroupScreen call not found")
main_activity.write_text(ma.replace(old_call, new_call, 1), encoding="utf-8")

# Android 13+ notification permission. The manifest declares the permission,
# but modern Android requires a runtime prompt before approval notifications
# can appear.
ma = main_activity.read_text(encoding="utf-8")
ma = ma.replace(
    "import android.content.Context\n",
    "import android.Manifest\n"
    "import android.content.Context\n"
    "import android.content.pm.PackageManager\n"
    "import android.os.Build\n",
    1,
)
ma = ma.replace(
    "import androidx.fragment.app.FragmentActivity\n",
    "import androidx.fragment.app.FragmentActivity\n"
    "import androidx.core.content.ContextCompat\n",
    1,
)
oncreate_anchor = """        super.onCreate(savedInstanceState)

        val app = application as? KeepMobileApp ?: run { finish(); return }
"""
oncreate_replacement = """        super.onCreate(savedInstanceState)

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
"""
if oncreate_anchor not in ma:
    raise SystemExit("MainActivity onCreate anchor not found")
ma = ma.replace(oncreate_anchor, oncreate_replacement, 1)
main_activity.write_text(ma, encoding="utf-8")


share_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_share.xml"
ss = share_strings.read_text(encoding="utf-8")
offline_strings = """
    <!-- Igloo Mobile advanced offline trusted-dealer setup -->
    <string name="igloo_offline_tab">Shares / Rotate</string>
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
"""
if "</resources>" not in ss:
    raise SystemExit("strings_share.xml missing resources terminator")
share_strings.write_text(ss.replace("</resources>", offline_strings + "</resources>", 1), encoding="utf-8")



# Harden bunker foreground notification paths. A failed notification or FGS
# promotion should set an error state instead of taking down the whole process.
bunker_service = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "nip46" / "BunkerService.kt"
bs = bunker_service.read_text(encoding="utf-8")
old_start = """        startForeground(NOTIFICATION_ID, createNotification(isActive = false))
"""
new_start = """        try {
            startForeground(NOTIFICATION_ID, createNotification(isActive = false))
        } catch (e: Exception) {
            if (BuildConfig.DEBUG) Log.e(TAG, "Unable to enter foreground mode", e)
            _status.value = BunkerStatus.ERROR
            stopSelf()
            return START_NOT_STICKY
        }
"""
if old_start not in bs:
    raise SystemExit("BunkerService startForeground anchor not found")
bs = bs.replace(old_start, new_start, 1)

old_update = """    private fun updateNotification(isActive: Boolean) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, createNotification(isActive))
    }
"""
new_update = """    private fun updateNotification(isActive: Boolean) {
        val manager = getSystemService(NotificationManager::class.java)
        runCatching {
            manager.notify(NOTIFICATION_ID, createNotification(isActive))
        }.onFailure {
            if (BuildConfig.DEBUG) Log.e(TAG, "Failed to update bunker notification", it)
        }
    }
"""
if old_update not in bs:
    raise SystemExit("BunkerService updateNotification anchor not found")
bs = bs.replace(old_update, new_update, 1)
bunker_service.write_text(bs, encoding="utf-8")

connections_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_connections.xml"
cs = connections_strings.read_text(encoding="utf-8")
cs = cs.replace(
    '<string name="connections_bunker_rotate_url_button">Rotate Bunker URL</string>',
    '<string name="connections_bunker_rotate_url_button">Rotate NIP-46 connection keys</string>',
    1,
)
cs = cs.replace(
    '<string name="connections_bunker_rotate_url_title">Rotate Bunker URL</string>',
    '<string name="connections_bunker_rotate_url_title">Rotate NIP-46 connection keys</string>',
    1,
)
cs = cs.replace(
    '<string name="connections_bunker_rotate_url_confirm">Rotate URL</string>',
    '<string name="connections_bunker_rotate_url_confirm">Rotate keys</string>',
    1,
)
connections_strings.write_text(cs, encoding="utf-8")



# Expose proactive FROST share refresh to Android. This requires the COMPLETE
# current share set and preserves the group public key/npub while replacing all
# signing shares. It is intentionally an offline trusted-device operation.
keep_mobile_rs = root / "keep" / "keep-mobile" / "src" / "lib.rs"
km = keep_mobile_rs.read_text(encoding="utf-8")
refresh_anchor = """    /// FFI split, option B (§8): mint (or re-mint) this device's per-group DKG
"""
refresh_method = r'''    /// Refresh an existing complete FROST share set offline.
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
        Self::validate_share_name(&name)?;
        if share_data.is_empty() || share_data.len() != passphrases.len() {
            return Err(KeepMobileError::InvalidShare {
                msg: "Provide every share and one passphrase per share".into(),
            });
        }

        let share_data: Vec<Zeroizing<String>> =
            share_data.into_iter().map(Zeroizing::new).collect();
        let passphrases: Vec<Zeroizing<String>> =
            passphrases.into_iter().map(Zeroizing::new).collect();

        let mut shares = Vec::with_capacity(share_data.len());
        for (data, passphrase) in share_data.iter().zip(passphrases.iter()) {
            let export = ShareExport::parse(data.as_str())
                .map_err(|e| KeepMobileError::InvalidShare { msg: e.to_string() })?;
            if export.ciphersuite != keep_core::frost::Ciphersuite::Secp256k1Tr {
                return Err(KeepMobileError::InvalidShare {
                    msg: "Only secp256k1 (Bitcoin/Nostr) shares are supported".into(),
                });
            }
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

        let new_passphrase = Zeroizing::new(new_passphrase);
        Self::build_generation_result(&refreshed, &new_passphrase)
    }

'''
if refresh_anchor not in km:
    raise SystemExit("KeepMobile FROST DKG anchor not found")
km = km.replace(refresh_anchor, refresh_method + refresh_anchor, 1)
keep_mobile_rs.write_text(km, encoding="utf-8")



# Amber-style NIP-46 signing approval notifications with inline Approve/Reject
# actions. Do not force-launch an activity from the background; tapping the
# notification still opens the detailed approval screen.
approval_receiver = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "nip46" / "Nip46ApprovalActionReceiver.kt"
approval_receiver.write_text(r'''package io.privkey.keep.nip46

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class Nip46ApprovalActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val requestId = intent.getStringExtra(EXTRA_REQUEST_ID) ?: return
        if (intent.action == ACTION_REJECT) {
            BunkerService.respondToApproval(requestId, false)
        }
    }

    companion object {
        const val ACTION_REJECT = "org.glowstr.frostfedbunker.NIP46_REJECT"
        const val EXTRA_REQUEST_ID = "nip46_approval_request_id"
    }
}
''', encoding="utf-8")

# Register the private receiver.
manifest = root / "app" / "src" / "main" / "AndroidManifest.xml"
mt = manifest.read_text(encoding="utf-8")
receiver_xml = """
        <receiver
            android:name=".nip46.Nip46ApprovalActionReceiver"
            android:enabled="true"
            android:exported="false" />

"""
if receiver_xml.strip() not in mt:
    mt = mt.replace(
        "        <service\n            android:name=\".nip46.BunkerService\"",
        receiver_xml + "        <service\n            android:name=\".nip46.BunkerService\"",
        1,
    )
manifest.write_text(mt, encoding="utf-8")

bunker_service = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "nip46" / "BunkerService.kt"
bs = bunker_service.read_text(encoding="utf-8")
bs = bs.replace(
    """        runCatching { startActivity(intent) }
        postApprovalNotification(requestId, request, intent)
""",
    """        postApprovalNotification(requestId, request, intent)
""",
    1,
)

notify_anchor = """        val appLabel = sanitizeDisplayName(request.appName).ifBlank { truncatePubkey(request.appPubkey) }
        val body = getString(R.string.bunker_approval_notification_text, appLabel, sanitizeDisplayName(request.method))
"""
notify_replacement = """        // Approval must still pass through Nip46ApprovalActivity so the
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
        val appLabel = sanitizeDisplayName(request.appName).ifBlank { truncatePubkey(request.appPubkey) }
        val body = getString(R.string.bunker_approval_notification_text, appLabel, sanitizeDisplayName(request.method))
"""
if notify_anchor not in bs:
    raise SystemExit("NIP-46 approval notification anchor not found")
bs = bs.replace(notify_anchor, notify_replacement, 1)

action_anchor = """            .setContentIntent(contentIntent)
            .setFullScreenIntent(contentIntent, true)
            .setAutoCancel(true)
"""
action_replacement = """            .setContentIntent(contentIntent)
            .setFullScreenIntent(contentIntent, true)
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
"""
if action_anchor not in bs:
    raise SystemExit("NIP-46 notification action anchor not found")
bs = bs.replace(action_anchor, action_replacement, 1)
bunker_service.write_text(bs, encoding="utf-8")



# Persist the last uncaught Android exception and include it in the existing
# diagnostics export. This gives the next runtime crash a usable stack trace.
keep_app = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "KeepMobileApp.kt"
ka = keep_app.read_text(encoding="utf-8")
ka = ka.replace(
    """    override fun onCreate() {
        super.onCreate()
        initializeKeepMobile()
""",
    """    override fun onCreate() {
        super.onCreate()
        installCrashCapture()
        initializeKeepMobile()
""",
    1,
)
crash_method_anchor = """    private fun initializeKeepMobile() {
"""
crash_method = r'''    private fun installCrashCapture() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            runCatching {
                val crashFile = java.io.File(filesDir, "last_crash.txt")
                val report = buildString {
                    appendLine("timestamp=" + java.time.Instant.now().toString())
                    appendLine("thread=" + thread.name)
                    appendLine("exception=" + throwable::class.java.name)
                    appendLine("message=" + (throwable.message ?: ""))
                    appendLine()
                    appendLine(throwable.stackTraceToString())
                }
                crashFile.writeText(report, Charsets.UTF_8)
            }
            if (previous != null) {
                previous.uncaughtException(thread, throwable)
            } else {
                android.os.Process.killProcess(android.os.Process.myPid())
                kotlin.system.exitProcess(10)
            }
        }
    }

'''
if crash_method_anchor not in ka:
    raise SystemExit("KeepMobileApp crash-method anchor not found")
ka = ka.replace(crash_method_anchor, crash_method + crash_method_anchor, 1)
keep_app.write_text(ka, encoding="utf-8")

export_logs = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "ExportLogsScreen.kt"
el = export_logs.read_text(encoding="utf-8")
el = el.replace(
    "import android.content.ActivityNotFoundException\n",
    "import android.content.ActivityNotFoundException\nimport android.content.Context\n",
    1,
)
el = el.replace(
    """                    buildExportContent(
                        keepMobile = keepMobile,
""",
    """                    buildExportContent(
                        context = context,
                        keepMobile = keepMobile,
""",
    1,
)
el = el.replace(
    """private suspend fun buildExportContent(
    keepMobile: KeepMobile,
""",
    """private suspend fun buildExportContent(
    context: Context,
    keepMobile: KeepMobile,
""",
    1,
)
crash_read_anchor = """    return buildString {
        appendLine("=== Keep Diagnostics ===")
"""
crash_read_replacement = r'''    val lastCrash = runCatching {
        File(context.filesDir, "last_crash.txt")
            .takeIf { it.isFile }
            ?.readText(Charsets.UTF_8)
            ?.take(100_000)
    }.getOrNull()

    return buildString {
        appendLine("=== Keep Diagnostics ===")
'''
if crash_read_anchor not in el:
    raise SystemExit("ExportLogs buildString anchor not found")
el = el.replace(crash_read_anchor, crash_read_replacement, 1)

activity_tail = """        if (activityLogResult == null) {
            appendLine("(unavailable)")
        } else {
            val (text, exported, total) = activityLogResult
            if (total > exported) {
                appendLine("(truncated to $exported of $total entries)")
            }
            if (text.isBlank()) appendLine("(no activity)") else appendLine(text)
        }
"""
activity_replacement = activity_tail + r'''        appendLine()
        appendLine("=== Last Uncaught Crash ===")
        if (lastCrash.isNullOrBlank()) {
            appendLine("(none captured)")
        } else {
            appendLine(lastCrash)
        }
'''
if activity_tail not in el:
    raise SystemExit("ExportLogs activity tail not found")
el = el.replace(activity_tail, activity_replacement, 1)
export_logs.write_text(el, encoding="utf-8")


# Keep NIP-46 signing requests as normal high-priority approval notifications,
# not alarm/call-style full-screen notifications.
bunker_service = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "nip46" / "BunkerService.kt"
bs = bunker_service.read_text(encoding="utf-8")
bs = bs.replace("            .setFullScreenIntent(contentIntent, true)\n", "")
bunker_service.write_text(bs, encoding="utf-8")



# FROSTFED_BACK_NAVIGATION_FIX
# Upstream MainScreen renders most detail flows as boolean-controlled full-screen
# composables rather than NavHost destinations. Without a Compose BackHandler,
# Android back falls through to the single MainActivity and finishes the app.
# Intercept back only while a transient screen is visible and mirror each
# screen's normal onDismiss cleanup.
main_activity = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "MainActivity.kt"
ma = main_activity.read_text(encoding="utf-8")
if "import androidx.activity.compose.BackHandler\n" not in ma:
    ma = ma.replace(
        "import androidx.activity.compose.setContent\n",
        "import androidx.activity.compose.BackHandler\n"
        "import androidx.activity.compose.setContent\n",
        1,
    )

back_anchor = """    LaunchedEffect(relays) {
        accountActions.setCurrentRelays(relays)
    }

"""
back_block = """    LaunchedEffect(relays) {
        accountActions.setCurrentRelays(relays)
    }

    val hasTransientScreen =
        showPinSetup ||
        showSecuritySettings ||
        showExportLogs ||
        showEventLog ||
        showBackupRestore ||
        showRecoverNsec ||
        showSignPolicyScreen ||
        showRelayAuthWhitelistScreen ||
        showPermissionsScreen ||
        showHistoryScreen ||
        showExportScreen ||
        showExportNcryptsecScreen ||
        showShareDetails ||
        showConnectedApps ||
        showBunkerScreen ||
        showWalletDescriptorScreen ||
        showAccountSwitcher ||
        showImportScreen ||
        showCreateGroupScreen ||
        showImportNsecScreen ||
        showCreateAccountScreen ||
        showSeedWordsScreen ||
        showMnemonicRecoveryScreen

    BackHandler(enabled = hasTransientScreen) {
        when {
            showPinSetup -> showPinSetup = false
            showSecuritySettings -> showSecuritySettings = false
            showExportLogs -> showExportLogs = false
            showEventLog -> showEventLog = false
            showBackupRestore -> showBackupRestore = false
            showRecoverNsec -> showRecoverNsec = false
            showSignPolicyScreen -> showSignPolicyScreen = false
            showRelayAuthWhitelistScreen -> showRelayAuthWhitelistScreen = false
            showPermissionsScreen -> showPermissionsScreen = false
            showHistoryScreen -> showHistoryScreen = false
            showExportScreen -> showExportScreen = false
            showExportNcryptsecScreen -> showExportNcryptsecScreen = false
            showShareDetails -> showShareDetails = false
            showConnectedApps && selectedAppPackage != null -> selectedAppPackage = null
            showConnectedApps -> showConnectedApps = false
            showBunkerScreen -> showBunkerScreen = false
            showWalletDescriptorScreen -> showWalletDescriptorScreen = false
            showAccountSwitcher -> showAccountSwitcher = false
            showImportScreen -> {
                showImportScreen = false
                importState = ImportState.Idle
            }
            showCreateGroupScreen -> {
                createGroupRun += 1
                accountActions.cancelDkg()
                showCreateGroupScreen = false
                createGroupState = CreateGroupState.Idle
            }
            showImportNsecScreen -> {
                showImportNsecScreen = false
                importState = ImportState.Idle
            }
            showCreateAccountScreen -> {
                showCreateAccountScreen = false
                importState = ImportState.Idle
            }
            showSeedWordsScreen -> {
                seedWordsRequestToken += 1
                seedWordsLoading = false
                seedWordsData.clear()
                showSeedWordsScreen = false
            }
            showMnemonicRecoveryScreen -> {
                showMnemonicRecoveryScreen = false
                importState = ImportState.Idle
            }
        }
    }

"""
if back_anchor not in ma:
    raise SystemExit("MainActivity BackHandler insertion anchor not found")
ma = ma.replace(back_anchor, back_block, 1)
main_activity.write_text(ma, encoding="utf-8")



# FROSTFED_METADATA_POLL_FIX
# The upstream UI polls keepMobile.getActiveShareMetadata() without establishing
# an authenticated share-decryption request context. That Rust path loads the
# encrypted share and therefore emits Storage errors every poll. The UI only
# needs the non-secret didBackup metadata here, which AndroidKeystoreStorage
# already exposes without decrypting FROST key material.
main_activity = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "MainActivity.kt"
ma = main_activity.read_text(encoding="utf-8")
old_poll = """                    val db = runCatching { keepMobile.getActiveShareMetadata()?.didBackup }
                        .onFailure { if (it is CancellationException) throw it }
                        .getOrNull()
"""
new_poll = """                    val db = runCatching { storage.getShareMetadata()?.didBackup }
                        .onFailure { if (it is CancellationException) throw it }
                        .getOrNull()
"""
if old_poll not in ma:
    raise SystemExit("MainActivity active-share metadata poll anchor not found")
ma = ma.replace(old_poll, new_poll, 1)
main_activity.write_text(ma, encoding="utf-8")

account_actions = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "AccountActions.kt"
aa = account_actions.read_text(encoding="utf-8")
old_refresh = """            val activeDidBackup = runCatching { keepMobile.getActiveShareMetadata()?.didBackup }
                .onFailure { Log.w("AccountActions", "getActiveShareMetadata failed: ${it::class.simpleName}") }
                .getOrNull()
"""
new_refresh = """            val activeDidBackup = runCatching { storage.getShareMetadata()?.didBackup }
                .onFailure { Log.w("AccountActions", "getShareMetadata failed: ${it::class.simpleName}") }
                .getOrNull()
"""
if old_refresh not in aa:
    raise SystemExit("AccountActions active-share metadata refresh anchor not found")
aa = aa.replace(old_refresh, new_refresh, 1)
account_actions.write_text(aa, encoding="utf-8")




# FROSTFED_DIRECT_SHARE_ROTATION_UI
# Surface the existing offline share-refresh engine directly from the active
# FROST account screen. Previously the code was only reachable by opening the
# create-group flow and switching to the offline tab, so existing users had no
# obvious "rotate shares" action.
create_group = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "CreateGroupScreen.kt"
cg = create_group.read_text(encoding="utf-8")

rotation_wrapper_anchor = """private enum class GroupSetupMode { DISTRIBUTED, JOIN, OFFLINE }

@Composable
private fun OfflineGroupMode(keepMobile: KeepMobile) {
"""
rotation_wrapper = """@Composable
fun FrostShareRotationScreen(
    keepMobile: KeepMobile,
    onDismiss: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Rotate FROST Shares",
            style = MaterialTheme.typography.headlineMedium
        )
        Spacer(modifier = Modifier.height(16.dp))
        OfflineRefreshMode(keepMobile = keepMobile, onBack = onDismiss)
    }
}

private enum class GroupSetupMode { DISTRIBUTED, JOIN, OFFLINE }

@Composable
private fun OfflineGroupMode(keepMobile: KeepMobile) {
"""
if rotation_wrapper_anchor not in cg:
    raise SystemExit("share rotation wrapper anchor not found")
cg = cg.replace(rotation_wrapper_anchor, rotation_wrapper, 1)
create_group.write_text(cg, encoding="utf-8")

main_activity = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "MainActivity.kt"
ma = main_activity.read_text(encoding="utf-8")

state_anchor = """    var showCreateGroupScreen by remember { mutableStateOf(false) }
"""
state_replacement = """    var showCreateGroupScreen by remember { mutableStateOf(false) }
    var showShareRotationScreen by remember { mutableStateOf(false) }
"""
if state_anchor not in ma:
    raise SystemExit("share rotation state anchor not found")
ma = ma.replace(state_anchor, state_replacement, 1)

transient_anchor = """        showImportScreen ||
        showCreateGroupScreen ||
        showImportNsecScreen ||
"""
transient_replacement = """        showImportScreen ||
        showCreateGroupScreen ||
        showShareRotationScreen ||
        showImportNsecScreen ||
"""
if transient_anchor not in ma:
    raise SystemExit("share rotation BackHandler enable anchor not found")
ma = ma.replace(transient_anchor, transient_replacement, 1)

back_case_anchor = """            showCreateGroupScreen -> {
                createGroupRun += 1
                accountActions.cancelDkg()
                showCreateGroupScreen = false
                createGroupState = CreateGroupState.Idle
            }
            showImportNsecScreen -> {
"""
back_case_replacement = """            showCreateGroupScreen -> {
                createGroupRun += 1
                accountActions.cancelDkg()
                showCreateGroupScreen = false
                createGroupState = CreateGroupState.Idle
            }
            showShareRotationScreen -> showShareRotationScreen = false
            showImportNsecScreen -> {
"""
if back_case_anchor not in ma:
    raise SystemExit("share rotation BackHandler case anchor not found")
ma = ma.replace(back_case_anchor, back_case_replacement, 1)

screen_anchor = """    if (showCreateGroupScreen) {
"""
screen_block = """    if (showShareRotationScreen) {
        FrostShareRotationScreen(
            keepMobile = keepMobile,
            onDismiss = { showShareRotationScreen = false }
        )
        return
    }

    if (showCreateGroupScreen) {
"""
if screen_anchor not in ma:
    raise SystemExit("share rotation screen insertion anchor not found")
ma = ma.replace(screen_anchor, screen_block, 1)

account_call_anchor = """                    onRecoverNsec = { showRecoverNsec = true },
                    onCreateGroup = { showCreateGroupScreen = true }
"""
account_call_replacement = """                    onRecoverNsec = { showRecoverNsec = true },
                    onRotateShares = { showShareRotationScreen = true },
                    onCreateGroup = { showCreateGroupScreen = true }
"""
if account_call_anchor not in ma:
    raise SystemExit("AccountTab call anchor not found")
ma = ma.replace(account_call_anchor, account_call_replacement, 1)

account_sig_anchor = """    onRecoverMnemonic: () -> Unit,
    onRecoverNsec: () -> Unit,
    onCreateGroup: () -> Unit
) {
"""
account_sig_replacement = """    onRecoverMnemonic: () -> Unit,
    onRecoverNsec: () -> Unit,
    onRotateShares: () -> Unit,
    onCreateGroup: () -> Unit
) {
"""
if account_sig_anchor not in ma:
    raise SystemExit("AccountTab signature anchor not found")
ma = ma.replace(account_sig_anchor, account_sig_replacement, 1)

button_anchor = """                    if (shareInfo.threshold >= 2u.toUShort()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = onRecoverNsec,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = MaterialTheme.colorScheme.error
                            )
                        ) {
                            Text(stringResource(R.string.main_recover_nsec_from_shares))
                        }
                    }
"""
button_replacement = """                    if (shareInfo.threshold >= 2u.toUShort()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = onRotateShares,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Rotate FROST Shares")
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = onRecoverNsec,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = MaterialTheme.colorScheme.error
                            )
                        ) {
                            Text(stringResource(R.string.main_recover_nsec_from_shares))
                        }
                    }
"""
if button_anchor not in ma:
    raise SystemExit("AccountTab threshold action anchor not found")
ma = ma.replace(button_anchor, button_replacement, 1)

main_activity.write_text(ma, encoding="utf-8")



# FROSTFED_SHARE_FILE_EXPORT
# Upstream only renders the encrypted kshare as QR/clipboard. Add a real
# Storage Access Framework "Save as" path, and keep the export session alive
# while Android's document picker temporarily pauses/stops the Activity.
export_share = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "ExportShareScreen.kt"
es = export_share.read_text(encoding="utf-8")

if "import androidx.activity.compose.rememberLauncherForActivityResult\n" not in es:
    es = es.replace(
        "import android.widget.Toast\n",
        "import android.widget.Toast\n"
        "import androidx.activity.compose.rememberLauncherForActivityResult\n"
        "import androidx.activity.result.contract.ActivityResultContracts\n",
        1,
    )

state_anchor = """    val sessionCanceled = remember { java.util.concurrent.atomic.AtomicBoolean(false) }
    val minLengthMessage = stringResource(R.string.export_share_min_length, MIN_PASSPHRASE_LENGTH)
"""
state_replacement = """    val sessionCanceled = remember { java.util.concurrent.atomic.AtomicBoolean(false) }
    var documentPickerActive by remember { mutableStateOf(false) }
    val documentPickerActiveState = rememberUpdatedState(documentPickerActive)
    val minLengthMessage = stringResource(R.string.export_share_min_length, MIN_PASSPHRASE_LENGTH)
"""
if state_anchor not in es:
    raise SystemExit("export file state anchor not found")
es = es.replace(state_anchor, state_replacement, 1)

messages_anchor = """    val authCancelledMessage = stringResource(R.string.export_share_auth_cancelled)
    val initFailedMessage = stringResource(R.string.export_share_init_failed)

    DisposableEffect(lifecycleOwner) {
"""
messages_replacement = """    val authCancelledMessage = stringResource(R.string.export_share_auth_cancelled)
    val initFailedMessage = stringResource(R.string.export_share_init_failed)

    val saveShareLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("text/plain")
    ) { uri ->
        documentPickerActive = false
        if (uri != null) {
            val exportData = (exportState as? ExportState.Success)?.data.orEmpty()
            if (exportData.isNotEmpty()) {
                coroutineScope.launch {
                    val saved = withContext(Dispatchers.IO) {
                        runCatching {
                            context.contentResolver.openOutputStream(uri, "wt")
                                ?.bufferedWriter(Charsets.UTF_8)
                                ?.use { writer ->
                                    writer.write(exportData)
                                    writer.newLine()
                                }
                                ?: error("Unable to open selected document")
                        }.isSuccess
                    }
                    Toast.makeText(
                        context,
                        if (saved) "Encrypted FROST share saved" else "Failed to save encrypted FROST share",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    DisposableEffect(lifecycleOwner) {
"""
if messages_anchor not in es:
    raise SystemExit("export file launcher anchor not found")
es = es.replace(messages_anchor, messages_replacement, 1)

lifecycle_anchor = """        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_PAUSE || event == Lifecycle.Event.ON_STOP) {
                clearSensitiveData()
            }
        }
"""
lifecycle_replacement = """        val observer = LifecycleEventObserver { _, event ->
            if (
                (event == Lifecycle.Event.ON_PAUSE || event == Lifecycle.Event.ON_STOP) &&
                !documentPickerActiveState.value
            ) {
                clearSensitiveData()
            }
        }
"""
if lifecycle_anchor not in es:
    raise SystemExit("export lifecycle anchor not found")
es = es.replace(lifecycle_anchor, lifecycle_replacement, 1)

success_call_anchor = """                ExportSuccessContent(
                    data = state.data,
                    frames = state.frames,
                    onDismiss = onDismiss
                )
"""
success_call_replacement = """                ExportSuccessContent(
                    data = state.data,
                    frames = state.frames,
                    onSaveToFile = {
                        documentPickerActive = true
                        val safeName = shareInfo.name
                            .replace(Regex("[^A-Za-z0-9._-]"), "_")
                            .take(48)
                            .ifBlank { "share" }
                        saveShareLauncher.launch("Frost-Fed-Bunker-" + safeName + ".kshare")
                    },
                    onDismiss = onDismiss
                )
"""
if success_call_anchor not in es:
    raise SystemExit("export success call anchor not found")
es = es.replace(success_call_anchor, success_call_replacement, 1)

success_sig_anchor = """private fun ExportSuccessContent(
    data: String,
    frames: List<String>,
    onDismiss: () -> Unit
) {
"""
success_sig_replacement = """private fun ExportSuccessContent(
    data: String,
    frames: List<String>,
    onSaveToFile: () -> Unit,
    onDismiss: () -> Unit
) {
"""
if success_sig_anchor not in es:
    raise SystemExit("ExportSuccessContent signature anchor not found")
es = es.replace(success_sig_anchor, success_sig_replacement, 1)

save_button_anchor = """    Spacer(modifier = Modifier.height(24.dp))

    OutlinedButton(
        onClick = { showClipboardWarning = true },
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(stringResource(R.string.export_share_copy_to_clipboard))
    }
"""
save_button_replacement = """    Spacer(modifier = Modifier.height(24.dp))

    Button(
        onClick = onSaveToFile,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text("Save encrypted share to file")
    }

    Spacer(modifier = Modifier.height(8.dp))

    OutlinedButton(
        onClick = { showClipboardWarning = true },
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(stringResource(R.string.export_share_copy_to_clipboard))
    }
"""
if save_button_anchor not in es:
    raise SystemExit("export save button anchor not found")
es = es.replace(save_button_anchor, save_button_replacement, 1)

export_share.write_text(es, encoding="utf-8")



# FROSTFED_PASTE_NSEC_IMPORT
# Make importing an existing Nostr account explicit: users can paste an nsec
# from the clipboard with one tap instead of relying on long-press paste.
import_nsec = root / "app" / "src" / "main" / "kotlin" / "io" / "privkey" / "keep" / "ImportNsecScreen.kt"
ins = import_nsec.read_text(encoding="utf-8")

if "import android.content.ClipboardManager\n" not in ins:
    ins = ins.replace(
        "package io.privkey.keep\n\n",
        "package io.privkey.keep\n\n"
        "import android.content.ClipboardManager\n"
        "import android.content.Context\n"
        "import android.widget.Toast\n",
        1,
    )

msg_anchor = """    val biometricUnavailableMsg = stringResource(R.string.import_nsec_biometric_unavailable)
    val cipherFailedMsg = stringResource(R.string.import_nsec_cipher_failed)
"""
msg_replacement = """    val biometricUnavailableMsg = stringResource(R.string.import_nsec_biometric_unavailable)
    val cipherFailedMsg = stringResource(R.string.import_nsec_cipher_failed)
    val pasteEmptyMsg = stringResource(R.string.import_nsec_paste_empty)
    val pasteInvalidMsg = stringResource(R.string.import_nsec_paste_invalid)
    val pasteTooLongMsg = stringResource(R.string.import_nsec_paste_too_long)
    val pastedMsg = stringResource(R.string.import_nsec_pasted)
"""
if msg_anchor not in ins:
    raise SystemExit("ImportNsec message anchor not found")
ins = ins.replace(msg_anchor, msg_replacement, 1)

button_anchor = """        Spacer(modifier = Modifier.height(8.dp))

        OutlinedButton(
            onClick = { showScanner = true },
            modifier = Modifier.fillMaxWidth(),
            enabled = isInputEnabled
        ) {
            Text(stringResource(R.string.import_nsec_scan_qr))
        }

        Spacer(modifier = Modifier.height(16.dp))
"""
button_replacement = """        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val pasted = clipboard.primaryClip
                    ?.takeIf { it.itemCount > 0 }
                    ?.getItemAt(0)
                    ?.coerceToText(context)
                    ?.toString()
                    ?.trim()
                    .orEmpty()

                when {
                    pasted.isBlank() -> scanError = pasteEmptyMsg
                    pasted.length > MAX_NSEC_LENGTH -> scanError = pasteTooLongMsg
                    !isValidNsecFormat(pasted) -> scanError = pasteInvalidMsg
                    else -> {
                        scanError = null
                        nsecData.update(pasted)
                        nsecDisplay = pasted
                        // Reduce the lifetime of the private key in the system clipboard
                        // after a successful explicit paste.
                        runCatching { clipboard.clearPrimaryClip() }
                        Toast.makeText(context, pastedMsg, Toast.LENGTH_SHORT).show()
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = isInputEnabled
        ) {
            Text(stringResource(R.string.import_nsec_paste))
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedButton(
            onClick = { showScanner = true },
            modifier = Modifier.fillMaxWidth(),
            enabled = isInputEnabled
        ) {
            Text(stringResource(R.string.import_nsec_scan_qr))
        }

        Spacer(modifier = Modifier.height(16.dp))
"""
if button_anchor not in ins:
    raise SystemExit("ImportNsec button anchor not found")
ins = ins.replace(button_anchor, button_replacement, 1)

import_nsec.write_text(ins, encoding="utf-8")

backup_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_backup.xml"
sb = backup_strings.read_text(encoding="utf-8")
strings_anchor = """    <string name="import_nsec_scan_qr">Scan QR Code</string>
    <string name="import_nsec_key_name_label">Key Name</string>
"""
strings_replacement = """    <string name="import_nsec_scan_qr">Scan QR Code</string>
    <string name="import_nsec_paste">Paste nsec</string>
    <string name="import_nsec_paste_empty">Clipboard is empty</string>
    <string name="import_nsec_paste_invalid">Clipboard does not contain a valid nsec1 private key</string>
    <string name="import_nsec_paste_too_long">Clipboard content is too long to be an nsec</string>
    <string name="import_nsec_pasted">nsec pasted securely; clipboard cleared</string>
    <string name="import_nsec_key_name_label">Account Name</string>
"""
if strings_anchor not in sb:
    raise SystemExit("ImportNsec string anchor not found")
sb = sb.replace(strings_anchor, strings_replacement, 1)
backup_strings.write_text(sb, encoding="utf-8")

main_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_main.xml"
ms = main_strings.read_text(encoding="utf-8")
ms = ms.replace(
    '<string name="main_import_nsec_button">Import nsec</string>',
    '<string name="main_import_nsec_button">Import / paste nsec</string>',
    1,
)
ms = ms.replace(
    '<string name="account_import_nsec">Import nsec</string>',
    '<string name="account_import_nsec">Import / paste nsec</string>',
    1,
)
main_strings.write_text(ms, encoding="utf-8")

print("Frost Fed Bunker FROSTR overlay applied successfully")
