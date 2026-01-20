# 백링크 자동 글쓰기 Windows EXE 빌드 스크립트 (PowerShell)
# 관리자 권한으로 실행 권장

Write-Host "=== 백링크 자동 글쓰기 Windows EXE 빌드 시작 ===" -ForegroundColor Cyan

# 스크립트 디렉토리로 이동
Set-Location $PSScriptRoot

# 기존 빌드 파일 정리
Write-Host "기존 빌드 파일 정리중..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Get-ChildItem -Filter "*.spec" | Remove-Item -Force

# 필수 패키지 설치
Write-Host "필수 패키지 확인 및 설치중..." -ForegroundColor Yellow
pip install pyinstaller selenium --quiet

# PyInstaller로 빌드
Write-Host "`nPyInstaller 빌드 시작..." -ForegroundColor Green

$pyinstallerArgs = @(
    "--name", "백링크자동글쓰기",
    "--onefile",
    "--windowed",
    "--hidden-import=tkinter",
    "--hidden-import=selenium",
    "--hidden-import=selenium.webdriver",
    "--hidden-import=selenium.webdriver.chrome",
    "--hidden-import=selenium.webdriver.chrome.service",
    "--hidden-import=selenium.webdriver.chrome.options",
    "--hidden-import=selenium.webdriver.common.by",
    "--hidden-import=selenium.webdriver.support.ui",
    "--hidden-import=selenium.webdriver.support.expected_conditions",
    "--hidden-import=selenium.common.exceptions",
    "--collect-all", "selenium",
    "backlink_auto_writer.py"
)

& pyinstaller $pyinstallerArgs

# 결과 확인
Write-Host "`n=== 빌드 완료 ===" -ForegroundColor Cyan

$exePath = Join-Path $PSScriptRoot "dist\백링크자동글쓰기.exe"
if (Test-Path $exePath) {
    $fileInfo = Get-Item $exePath
    Write-Host "`nEXE 파일 생성 성공!" -ForegroundColor Green
    Write-Host "위치: $exePath"
    Write-Host "크기: $([math]::Round($fileInfo.Length / 1MB, 2)) MB"
} else {
    Write-Host "`n빌드 실패 - EXE 파일이 생성되지 않았습니다." -ForegroundColor Red
}

Write-Host "`n사용 방법:" -ForegroundColor Yellow
Write-Host "1. dist 폴더의 '백링크자동글쓰기.exe' 파일을 원하는 위치로 복사"
Write-Host "2. 더블클릭하여 실행"

Write-Host "`n주의사항:" -ForegroundColor Yellow
Write-Host "- Chrome 브라우저가 설치되어 있어야 합니다"
Write-Host "- 인터넷 연결이 필요합니다 (구글시트 데이터 로드)"

Write-Host "`n"
Read-Host "계속하려면 Enter를 누르세요"
