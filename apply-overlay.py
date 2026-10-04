#!/usr/bin/env python3
# Frost Fed Bunker Android overlay.
"""Apply the minimal Igloo Mobile overlay to a pinned Keep Android checkout."""

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
replace_once(gradle, 'applicationId = "io.privkey.keep"', 'applicationId = "org.glowstr.igloomobile"')
replace_once(gradle, 'versionCode = 28', 'versionCode = 1')
replace_once(gradle, 'versionName = "1.2.0"', 'versionName = "0.1.0-test"')
replace_once(
    gradle,
    'include("arm64-v8a", "x86_64")',
    'include("arm64-v8a")',
)

strings = root / "app" / "src" / "main" / "res" / "values" / "strings.xml"
replace_once(
    strings,
    '<string name="app_name" translatable="false">Keep</string>',
    '<string name="app_name" translatable="false">Igloo Mobile</string>',
)
replace_once(
    strings,
    '<string name="foreground_service_title" translatable="false">Keep</string>',
    '<string name="foreground_service_title" translatable="false">Igloo Mobile</string>',
)
replace_once(
    strings,
    '<string name="bunker_service_title" translatable="false">Keep Bunker</string>',
    '<string name="bunker_service_title" translatable="false">Igloo Mobile Bunker</string>',
)
replace_once(
    strings,
    '<string name="biometric_unlock_title" translatable="false">Keep</string>',
    '<string name="biometric_unlock_title" translatable="false">Igloo Mobile</string>',
)

main_strings = root / "app" / "src" / "main" / "res" / "values" / "strings_main.xml"
replace_once(
    main_strings,
    '<string name="main_unlock_title">Unlock Keep</string>',
    '<string name="main_unlock_title">Unlock Igloo Mobile</string>',
)
replace_once(
    main_strings,
    '<string name="main_home_title">Keep</string>',
    '<string name="main_home_title">Igloo Mobile</string>',
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
    '<string name="connections_bunker_rotate_url_button">Rotate bunker URL</string>',
    '<string name="connections_bunker_rotate_url_button">Rotate NIP-46 connection keys</string>',
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
        when (intent.action) {
            ACTION_APPROVE -> BunkerService.respondToApproval(requestId, true)
            ACTION_REJECT -> BunkerService.respondToApproval(requestId, false)
        }
    }

    companion object {
        const val ACTION_APPROVE = "org.glowstr.igloomobile.NIP46_APPROVE"
        const val ACTION_REJECT = "org.glowstr.igloomobile.NIP46_REJECT"
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
notify_replacement = """        val approveIntent = PendingIntent.getBroadcast(
            this,
            notificationId * 2 + 1,
            Intent(this, Nip46ApprovalActionReceiver::class.java)
                .setAction(Nip46ApprovalActionReceiver.ACTION_APPROVE)
                .putExtra(Nip46ApprovalActionReceiver.EXTRA_REQUEST_ID, requestId),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
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

print("Igloo Mobile overlay applied successfully")
