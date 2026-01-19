#!/bin/bash
# 백링크 자동 글쓰기 Mac 앱 빌드 스크립트

cd /Users/deneb/linkauto

echo "=== 백링크 자동 글쓰기 Mac 앱 빌드 시작 ==="

# 기존 빌드 파일 정리
rm -rf build dist *.spec

# PyInstaller로 앱 빌드
pyinstaller --name "백링크자동글쓰기" \
    --windowed \
    --onefile \
    --hidden-import=tkinter \
    --hidden-import=selenium \
    --hidden-import=selenium.webdriver \
    --hidden-import=selenium.webdriver.chrome \
    --hidden-import=selenium.webdriver.chrome.service \
    --hidden-import=selenium.webdriver.chrome.options \
    --hidden-import=selenium.webdriver.common.by \
    --hidden-import=selenium.webdriver.support.ui \
    --hidden-import=selenium.webdriver.support.expected_conditions \
    --osx-bundle-identifier "com.linkauto.backlinkwriter" \
    backlink_auto_writer.py

echo ""
echo "=== 빌드 완료 ==="
echo "앱 위치: dist/백링크자동글쓰기.app"
echo ""
echo "설치 방법:"
echo "1. dist/백링크자동글쓰기.app 을 Applications 폴더로 드래그"
echo "2. 또는 더블클릭하여 바로 실행"
