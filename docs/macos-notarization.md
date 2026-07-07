# macOS Notarization Setup

The GitHub Actions workflow can create Apple-notarized DMG files when the required Apple secrets are configured. Without these secrets, macOS builds still run, but they are ad-hoc signed test builds and may be blocked by Gatekeeper.

Traditional Chinese: [macOS 公證設定](macos-notarization.zh_TW.md)

## What You Need

- An Apple Account with two-factor authentication enabled.
- An active Apple Developer Program membership.
- A Developer ID Application certificate exported as a password-protected `.p12` file.
- An App Store Connect API key for `notarytool`.
- GitHub repository secrets configured for this repository.

Apple documents the enrollment requirements at:

- <https://developer.apple.com/programs/enroll/>
- <https://developer.apple.com/help/account/certificates/create-developer-id-certificates>
- <https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api>
- <https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution>

## 1. Enroll in the Apple Developer Program

For an individual account, Apple requires an Apple Account with two-factor authentication, your legal name, email, phone, and address. The Apple Developer Program is 99 USD per membership year, with local pricing shown during enrollment.

Start here:

<https://developer.apple.com/programs/enroll/>

If you enroll as an individual, your personal legal name is used as the developer / seller name. If you enroll as an organization, Apple requires organization verification such as legal authority and a D-U-N-S Number.

## 2. Create a Developer ID Application Certificate

Use a Mac for this part.

1. Open **Keychain Access**.
2. Choose **Keychain Access > Certificate Assistant > Request a Certificate From a Certificate Authority**.
3. Enter your Apple Developer email and name.
4. Select **Saved to disk** and create a certificate signing request file.
5. Go to **Apple Developer > Certificates, Identifiers & Profiles > Certificates**.
6. Click **+**.
7. Under **Software**, choose **Developer ID Application**.
8. Upload the certificate signing request.
9. Download the generated certificate and open it on the Mac so it is added to Keychain Access.
10. In Keychain Access, export the Developer ID Application certificate together with its private key as a password-protected `.p12` file.

Do not commit the `.p12` file to the repository.

Convert the `.p12` file to one-line base64 for GitHub Secrets:

```bash
base64 -i DeveloperIDApplication.p12 | tr -d '\n' | pbcopy
```

## 3. Create an App Store Connect API Key

1. Go to **App Store Connect > Users and Access > Integrations**.
2. If required, click **Request Access** for the App Store Connect API.
3. Open **Team Keys**.
4. Click **Generate API Key**.
5. Choose a role that is allowed to submit notarization requests. `Developer` is usually enough; use `Admin` if the first notarization attempt is rejected for permissions.
6. Download the `.p8` private key. Apple only allows this download once.
7. Copy the **Key ID** and **Issuer ID**.

Do not commit the `.p8` file to the repository.

## 4. Add GitHub Secrets

In GitHub, open:

**Repository > Settings > Secrets and variables > Actions > New repository secret**

Add these secrets:

| Secret | Required | Value |
| --- | --- | --- |
| `APPLE_DEVELOPER_ID_CERTIFICATE_BASE64` | Yes | One-line base64 of the exported `.p12` certificate. |
| `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD` | Yes | Password used when exporting the `.p12` certificate. |
| `APPLE_CODESIGN_IDENTITY` | Optional | Example: `Developer ID Application: Your Name (TEAMID)`. If omitted, the workflow tries to detect it. |
| `APP_STORE_CONNECT_KEY_ID` | Yes | App Store Connect API key ID. |
| `APP_STORE_CONNECT_ISSUER_ID` | Yes | App Store Connect issuer ID. |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Yes | Full text contents of the downloaded `.p8` private key. |

## 5. Build a Notarized DMG

Run the **Build desktop apps** workflow manually, or push a version tag such as:

```bash
git tag v1.0.0
git push origin v1.0.0
```

When all required secrets are present, the macOS jobs will:

1. Import the Developer ID Application certificate into a temporary keychain.
2. Build the `.app`.
3. Sign the `.app` with hardened runtime.
4. Package the drag-to-Applications `.dmg`.
5. Sign the `.dmg`.
6. Submit the `.dmg` to Apple notarization with `xcrun notarytool`.
7. Staple the notarization ticket with `xcrun stapler`.
8. Verify the DMG with `spctl`.

If any required secret is missing, the workflow keeps producing ad-hoc signed test DMGs instead of failing the whole build.
