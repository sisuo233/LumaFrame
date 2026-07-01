# Android release signing

Release APK builds are signed in GitHub Actions with repository secrets. Do not
commit the keystore file or passwords to this public repository.

## 1. Generate a release keystore

Run this on a machine with Java installed:

```powershell
keytool -genkeypair -v `
  -keystore film-border-release.jks `
  -alias film-border `
  -keyalg RSA `
  -keysize 2048 `
  -validity 10000
```

Keep `film-border-release.jks` and its passwords backed up. If this key is lost,
future APK updates with the same Android package name cannot be signed with the
same identity.

## 2. Encode the keystore for GitHub

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("film-border-release.jks")) | Set-Clipboard
```

## 3. Add GitHub Actions secrets

Open:

```text
https://github.com/sisuo233/film-border/settings/secrets/actions
```

Create these repository secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Use the base64 text from the clipboard for `ANDROID_KEYSTORE_BASE64`.
Use the keystore password, key alias, and key password from step 1 for the other
three secrets.

## 4. Build

Run the `Build Android Release APK` workflow, or push to `main`. The workflow
will fail if any signing secret is missing, and it verifies the APK signature
before uploading the artifact.
