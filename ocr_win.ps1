# OCR con el motor nativo de Windows (Windows.Media.Ocr).
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File ocr_win.ps1 -Path imagen.png
# Devuelve JSON: { ok, texto, lineas[], idioma }
param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Await($op, [Type]$t) {
  $task = [System.WindowsRuntimeSystemExtensions].GetMethods() |
          Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                         $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } |
          Select-Object -First 1
  $m = $task.MakeGenericMethod($t)
  $r = $m.Invoke($null, @($op))
  $r.Wait(60000) | Out-Null
  return $r.Result
}

try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
  $null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
  $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
  $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]

  $full = (Resolve-Path -LiteralPath $Path).Path
  $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
  $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

  $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
  if ($null -eq $engine) {
    $langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages
    if ($langs.Count -gt 0) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($langs[0]) }
  }
  if ($null -eq $engine) { throw 'No hay motor de OCR disponible en este Windows.' }

  $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

  $lineas = @()
  foreach ($l in $result.Lines) { $lineas += $l.Text }

  $out = [ordered]@{
    ok     = $true
    idioma = $engine.RecognizerLanguage.LanguageTag
    lineas = $lineas
    texto  = ($lineas -join "`n")
  }
  $out | ConvertTo-Json -Depth 4 -Compress
}
catch {
  @{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress
  exit 1
}
