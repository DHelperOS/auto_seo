@echo off
chcp 65001 >nul
echo === 백링크 자동 글쓰기 Windows EXE 빌드 시작 ===

REM 현재 디렉토리 확인
cd /d "%~dp0"

REM 기존 빌드 파일 정리
echo 기존 빌드 파일 정리중...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

REM 필수 패키지 설치 확인
echo 필수 패키지 확인 및 설치중...
pip install pyinstaller selenium --quiet

REM PyInstaller로 EXE 빌드
echo.
echo PyInstaller 빌드 시작...
pyinstaller --name "백링크자동글쓰기" ^
    --onefile ^
    --windowed ^
    --hidden-import=tkinter ^
    --hidden-import=selenium ^
    --hidden-import=selenium.webdriver ^
    --hidden-import=selenium.webdriver.chrome ^
    --hidden-import=selenium.webdriver.chrome.service ^
    --hidden-import=selenium.webdriver.chrome.options ^
    --hidden-import=selenium.webdriver.common.by ^
    --hidden-import=selenium.webdriver.support.ui ^
    --hidden-import=selenium.webdriver.support.expected_conditions ^
    --hidden-import=selenium.common.exceptions ^
    --collect-all selenium ^
    backlink_auto_writer.py

echo.
echo === 빌드 완료 ===
echo.
echo EXE 파일 위치: dist\백링크자동글쓰기.exe
echo.
echo 사용 방법:
echo 1. dist 폴더의 "백링크자동글쓰기.exe" 파일을 원하는 위치로 복사
echo 2. 더블클릭하여 실행
echo.
echo 주의사항:
echo - Chrome 브라우저가 설치되어 있어야 합니다
echo - 인터넷 연결이 필요합니다 (구글시트 데이터 로드)
echo.
pause
