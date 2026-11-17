<#
  Gera as pastas android/ e ios/ (que não vêm no repositório) e aplica as configurações
  necessárias à Tastelume: permissão de Internet, tráfego HTTP em desenvolvimento e
  permissões da câmara/galeria.

  Uso (PowerShell, dentro de mobile_app/):
      .\setup_platforms.ps1
#>
$ErrorActionPreference = 'Stop'

if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw 'O comando "flutter" não foi encontrado. Instala o Flutter SDK e abre uma nova janela do PowerShell.'
}

flutter create --org pt.tastelume --project-name tastelume --platforms=android,ios .
if ($LASTEXITCODE -ne 0) { throw 'flutter create falhou.' }

# --- Android ---
$manifest = 'android\app\src\main\AndroidManifest.xml'
if (Test-Path $manifest) {
    $xml = Get-Content $manifest -Raw
    if ($xml -notmatch 'android.permission.INTERNET') {
        $xml = $xml.Replace('<application', "<uses-permission android:name=`"android.permission.INTERNET`"/>`r`n    <application")
    }
    if ($xml -notmatch 'usesCleartextTraffic') {
        # O backend de desenvolvimento usa HTTP (não HTTPS).
        $xml = $xml.Replace('<application', '<application android:usesCleartextTraffic="true"')
    }
    Set-Content -Path $manifest -Value $xml -Encoding UTF8
    Write-Host "Android: AndroidManifest.xml atualizado."
}

# --- iOS ---
$plist = 'ios\Runner\Info.plist'
if (Test-Path $plist) {
    $text = Get-Content $plist -Raw
    if ($text -notmatch 'NSCameraUsageDescription') {
        $extra = @'
	<key>NSCameraUsageDescription</key>
	<string>A Tastelume usa a câmara para fotografar as tuas receitas.</string>
	<key>NSPhotoLibraryUsageDescription</key>
	<string>A Tastelume acede à galeria para escolheres a foto da receita.</string>
	<key>NSAppTransportSecurity</key>
	<dict>
		<key>NSAllowsArbitraryLoads</key>
		<true/>
	</dict>
'@
        $idx = $text.LastIndexOf('</dict>')
        $text = $text.Substring(0, $idx) + $extra + "`r`n" + $text.Substring($idx)
        Set-Content -Path $plist -Value $text -Encoding UTF8
        Write-Host "iOS: Info.plist atualizado."
    }
}

flutter pub get
Write-Host "`nPronto. Próximos passos:`n  flutter analyze`n  flutter test`n  flutter run"
