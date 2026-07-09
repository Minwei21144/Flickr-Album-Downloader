# macOS 公證設定

GitHub Actions 已支援在設定 Apple secrets 後產生 Apple 公證過的 DMG。沒有設定 secrets 時，macOS 建置仍會繼續產出測試用 `.app.zip`，但它只會是 ad-hoc 簽章，解壓後第一次開啟 `.app` 時仍可能被 Gatekeeper 擋下。

English: [macOS notarization setup](macos-notarization.md)

## 你需要準備

- 已啟用雙重認證的 Apple ID / Apple Account。
- 有效的 Apple Developer Program 會員資格。
- 匯出成 `.p12` 的 Developer ID Application 憑證。
- 給 `notarytool` 使用的 App Store Connect API key。
- GitHub repository secrets。

Apple 官方文件：

- <https://developer.apple.com/programs/enroll/>
- <https://developer.apple.com/help/account/certificates/create-developer-id-certificates>
- <https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api>
- <https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution>

## 1. 註冊 Apple Developer Program

個人帳號需要 Apple ID 啟用雙重認證，並提供真實姓名、Email、電話與地址。Apple Developer Program 費用為每年 99 USD，實際會依地區顯示當地幣別。

從這裡開始：

<https://developer.apple.com/programs/enroll/>

若用個人身分註冊，對外顯示的開發者 / 銷售者名稱會是你的個人真實姓名。若用公司組織註冊，Apple 會要求組織驗證，例如法定代表權與 D-U-N-S Number。

## 2. 建立 Developer ID Application 憑證

這段需要在 Mac 上操作。

1. 打開 **鑰匙圈存取 / Keychain Access**。
2. 選擇 **Keychain Access > Certificate Assistant > Request a Certificate From a Certificate Authority**。
3. 輸入 Apple Developer Email 與名稱。
4. 選擇 **Saved to disk**，建立 certificate signing request 檔案。
5. 前往 **Apple Developer > Certificates, Identifiers & Profiles > Certificates**。
6. 點選 **+**。
7. 在 **Software** 底下選擇 **Developer ID Application**。
8. 上傳 certificate signing request。
9. 下載產生的憑證，並在 Mac 上開啟，讓它加入 Keychain Access。
10. 在 Keychain Access 裡，把 Developer ID Application 憑證連同 private key 匯出成有密碼保護的 `.p12` 檔案。

不要把 `.p12` 檔案 commit 到 repository。

把 `.p12` 轉成單行 base64，方便貼到 GitHub Secrets：

```bash
base64 -i DeveloperIDApplication.p12 | tr -d '\n' | pbcopy
```

## 3. 建立 App Store Connect API Key

1. 前往 **App Store Connect > Users and Access > Integrations**。
2. 如果頁面要求，先點選 **Request Access** 申請 App Store Connect API 使用權。
3. 打開 **Team Keys**。
4. 點選 **Generate API Key**。
5. 選擇允許提交公證請求的角色。通常 `Developer` 已足夠；若第一次公證因權限被拒，可改用 `Admin`。
6. 下載 `.p8` private key。Apple 只允許下載一次。
7. 記下 **Key ID** 與 **Issuer ID**。

不要把 `.p8` 檔案 commit 到 repository。

## 4. 新增 GitHub Secrets

在 GitHub repository 打開：

**Settings > Secrets and variables > Actions > New repository secret**

新增以下 secrets：

| Secret | 必填 | 內容 |
| --- | --- | --- |
| `APPLE_DEVELOPER_ID_CERTIFICATE_BASE64` | 是 | `.p12` 憑證轉成單行 base64 後的內容。 |
| `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD` | 是 | 匯出 `.p12` 時設定的密碼。 |
| `APPLE_CODESIGN_IDENTITY` | 選填 | 例如：`Developer ID Application: Your Name (TEAMID)`。不填時 workflow 會嘗試自動偵測。 |
| `APP_STORE_CONNECT_KEY_ID` | 是 | App Store Connect API Key ID。 |
| `APP_STORE_CONNECT_ISSUER_ID` | 是 | App Store Connect Issuer ID。 |
| `APP_STORE_CONNECT_PRIVATE_KEY` | 是 | 下載的 `.p8` private key 完整文字內容。 |

## 5. 建立公證過的 DMG

手動執行 **Build desktop apps** workflow，或推送版本 tag：

```bash
git tag v1.1.1
git push origin v1.1.1
```

當所有 secrets 都存在時，macOS jobs 會：

1. 把 Developer ID Application 憑證匯入暫存 keychain。
2. 建立 `.app`。
3. 使用 hardened runtime 簽署 `.app`。
4. 打包拖拉到 Applications 的 `.dmg`。
5. 簽署 `.dmg`。
6. 用 `xcrun notarytool` 送 Apple 公證。
7. 用 `xcrun stapler` 釘上公證票據。
8. 用 `spctl` 驗證 DMG。

如果少了任一必填 secret，workflow 不會直接失敗，而是維持產出 ad-hoc signed `.app.zip` 測試版。這種未簽章版本適合知道如何手動允許未知開發者 App 的使用者。請參考 [未簽章 macOS 安裝說明](macos-unsigned-install.zh_TW.md)。
