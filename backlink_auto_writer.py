#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백링크 자동 글쓰기 프로그램
그누보드 기반 사이트에 자동으로 글을 작성하는 GUI 프로그램
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import os
import threading
import random
import csv
import io
import urllib.request
import ssl
import time

# SSL 인증서 검증 우회
ssl._create_default_https_context = ssl._create_unverified_context

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 구글시트 설정
GOOGLE_SHEET_ID = "1WJqRvbYT8YiJE9cLyGVZHpbFecEkIhjkajtQg1x5CuM"
GOOGLE_SHEET_PRESET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"
GOOGLE_SHEET_URL_LIST_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=646237190"


class BacklinkAutoWriter:
    def __init__(self, root):
        self.root = root
        self.root.title("백링크 자동 글쓰기")
        self.root.geometry("900x700")

        # URL 리스트
        self.urls = []
        self.driver = None
        self.presets = []  # 프리셋 데이터 저장

        self.setup_ui()
        self.load_urls()
        self.load_presets_from_google_sheet()

    def setup_ui(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === 입력 정보 프레임 ===
        input_frame = ttk.LabelFrame(main_frame, text="입력 정보", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # 이름
        ttk.Label(input_frame, text="이름:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar(value="서우실장")
        self.name_entry = ttk.Entry(input_frame, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 20))

        # 비밀번호
        ttk.Label(input_frame, text="비밀번호:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value="p951219@")
        self.password_entry = ttk.Entry(input_frame, textvariable=self.password_var, width=30, show="*")
        self.password_entry.grid(row=0, column=3, sticky=tk.W, pady=2)

        # 프리셋 선택
        ttk.Label(input_frame, text="프리셋:").grid(row=1, column=0, sticky=tk.W, pady=2)
        preset_select_frame = ttk.Frame(input_frame)
        preset_select_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W+tk.E, pady=2, padx=(5, 0))

        self.preset_var = tk.StringVar(value="선택하세요")
        self.preset_combo = ttk.Combobox(preset_select_frame, textvariable=self.preset_var, width=40, state="readonly")
        self.preset_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)

        ttk.Button(preset_select_frame, text="🎲 랜덤 선택", command=self.select_random_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_select_frame, text="🔄 프리셋 새로고침", command=self.load_presets_from_google_sheet).pack(side=tk.LEFT, padx=5)

        # 제목
        title_label_frame = ttk.Frame(input_frame)
        title_label_frame.grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Label(title_label_frame, text="제목:").pack(side=tk.LEFT)
        ttk.Button(title_label_frame, text="📋", width=2, command=self.copy_title).pack(side=tk.LEFT, padx=2)

        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(input_frame, textvariable=self.title_var, width=80)
        self.title_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W+tk.E, pady=2, padx=(5, 0))

        # 내용
        content_label_frame = ttk.Frame(input_frame)
        content_label_frame.grid(row=3, column=0, sticky=tk.NW, pady=2)
        ttk.Label(content_label_frame, text="내용:").pack(anchor=tk.W)
        ttk.Button(content_label_frame, text="📋복사", width=6, command=self.copy_content).pack(anchor=tk.W, pady=5)

        self.content_text = scrolledtext.ScrolledText(input_frame, width=80, height=8)
        self.content_text.grid(row=3, column=1, columnspan=3, sticky=tk.W+tk.E, pady=2, padx=(5, 0))

        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

        # === URL 리스트 프레임 ===
        url_frame = ttk.LabelFrame(main_frame, text="URL 목록", padding="10")
        url_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 트리뷰 (URL 리스트)
        columns = ("번호", "캡차", "URL", "상태")
        self.url_tree = ttk.Treeview(url_frame, columns=columns, show="headings", height=15)
        self.url_tree.heading("번호", text="번호", command=lambda: self.sort_treeview("번호"))
        self.url_tree.heading("캡차", text="캡차", command=lambda: self.sort_treeview("캡차"))
        self.url_tree.heading("URL", text="URL", command=lambda: self.sort_treeview("URL"))
        self.url_tree.heading("상태", text="상태", command=lambda: self.sort_treeview("상태"))
        self.url_tree.column("번호", width=50, anchor=tk.CENTER)
        self.url_tree.column("캡차", width=50, anchor=tk.CENTER)
        self.url_tree.column("URL", width=550)
        self.url_tree.column("상태", width=100, anchor=tk.CENTER)
        self.sort_reverse = False  # 정렬 방향

        # 스크롤바
        scrollbar = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_tree.yview)
        self.url_tree.configure(yscrollcommand=scrollbar.set)

        self.url_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 더블클릭 이벤트
        self.url_tree.bind("<Double-1>", self.on_url_double_click)

        # === 버튼 프레임 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # 버튼들
        ttk.Button(button_frame, text="▶ 원클릭 실행", command=self.one_click_run).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="▶▶ 모든 프리셋 등록", command=self.register_all_presets).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="▶▶▶ 캡차없는 사이트 전체 자동등록", command=self.auto_register_all_no_captcha).pack(side=tk.LEFT, padx=5)

        # === 상태바 ===
        self.status_var = tk.StringVar(value="준비됨")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # Selenium 사용 불가 경고
        if not SELENIUM_AVAILABLE:
            self.status_var.set("경고: selenium이 설치되지 않음. pip install selenium 실행 필요")

    def load_urls(self):
        """구글시트에서 URL 목록 로드"""
        self.urls = []
        self.url_captcha_info = []  # 캡차 정보 저장
        self.url_tree.delete(*self.url_tree.get_children())

        try:
            self.status_var.set("구글시트에서 URL 로드 중...")
            self.root.update()

            # CSV 데이터 가져오기
            req = urllib.request.Request(
                GOOGLE_SHEET_URL_LIST_URL,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                csv_data = response.read().decode('utf-8')

            # CSV 파싱 (A열: URL, B열: 캡차여부)
            reader = csv.reader(io.StringIO(csv_data))
            for i, row in enumerate(reader, 1):
                if row and row[0].strip():
                    url = row[0].strip()
                    # URL 형식 확인 (http로 시작하는 것만)
                    if url.startswith('http'):
                        # B열에서 캡차 여부 확인
                        has_captcha = False
                        if len(row) > 1:
                            captcha_val = row[1].strip().upper()
                            has_captcha = captcha_val in ['TRUE', 'O', 'YES', '1', 'Y']

                        self.urls.append(url)
                        self.url_captcha_info.append(has_captcha)

                        # 캡차 표시: ✓(있음) 또는 빈칸(없음)
                        captcha_mark = "✓" if has_captcha else ""
                        self.url_tree.insert("", tk.END, values=(len(self.urls), captcha_mark, url, "대기"))

            self.status_var.set(f"총 {len(self.urls)}개의 URL 로드됨 (캡차있음: {sum(self.url_captcha_info)}개)")
        except Exception as e:
            self.status_var.set(f"URL 로드 실패: {str(e)}")
            messagebox.showerror("오류", f"구글시트 URL 로드 오류:\n{str(e)}")

    def sort_treeview(self, col):
        """트리뷰 정렬"""
        # 현재 데이터 가져오기
        items = [(self.url_tree.set(item, col), item) for item in self.url_tree.get_children('')]

        # 정렬 (번호는 숫자로, 나머지는 문자열로)
        if col == "번호":
            items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=self.sort_reverse)
        else:
            items.sort(key=lambda x: x[0], reverse=self.sort_reverse)

        # 재배치
        for index, (val, item) in enumerate(items):
            self.url_tree.move(item, '', index)

        # 정렬 방향 토글
        self.sort_reverse = not self.sort_reverse

    def load_presets_from_google_sheet(self):
        """구글시트에서 프리셋 데이터 로드"""
        self.presets = []

        try:
            self.status_var.set("구글시트에서 프리셋 로드 중...")
            self.root.update()

            # CSV 데이터 가져오기
            req = urllib.request.Request(
                GOOGLE_SHEET_PRESET_URL,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                csv_data = response.read().decode('utf-8')

            # CSV 파싱 (컬럼명 공백 제거)
            reader = csv.DictReader(io.StringIO(csv_data))
            for row in reader:
                # 컬럼명에 공백이 있을 수 있으므로 strip 처리
                clean_row = {k.strip(): v for k, v in row.items() if k}
                preset_name = clean_row.get('프리셋명', '').strip()
                title = clean_row.get('제목', '').strip()
                content = clean_row.get('내용', '').strip()

                if preset_name and (title or content):
                    self.presets.append({
                        'name': preset_name,
                        'title': title,
                        'content': content
                    })

            # 콤보박스 업데이트
            preset_names = [p['name'] for p in self.presets]
            self.preset_combo['values'] = preset_names if preset_names else ["프리셋 없음"]

            if preset_names:
                self.preset_var.set("선택하세요")
                self.status_var.set(f"프리셋 {len(self.presets)}개 로드 완료")
            else:
                self.preset_var.set("프리셋 없음")
                self.status_var.set("구글시트에 프리셋 데이터가 없습니다")

        except Exception as e:
            self.status_var.set(f"프리셋 로드 실패: {str(e)}")
            self.preset_combo['values'] = ["로드 실패"]
            self.preset_var.set("로드 실패")

    def on_preset_selected(self, event=None):
        """프리셋 선택 시 제목과 내용 자동 입력"""
        selected_name = self.preset_var.get()

        for preset in self.presets:
            if preset['name'] == selected_name:
                # 제목 입력
                self.title_var.set(preset['title'])

                # 내용 입력
                self.content_text.delete("1.0", tk.END)
                self.content_text.insert("1.0", preset['content'])

                self.status_var.set(f"프리셋 '{selected_name}' 적용됨")
                break

    def copy_title(self):
        """제목을 클립보드에 복사"""
        title = self.title_var.get().strip()
        if title:
            self.root.clipboard_clear()
            self.root.clipboard_append(title)
            self.status_var.set("제목이 클립보드에 복사되었습니다.")
        else:
            self.status_var.set("복사할 제목이 없습니다.")

    def copy_content(self):
        """내용을 클립보드에 복사"""
        content = self.content_text.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("내용이 클립보드에 복사되었습니다.")
        else:
            self.status_var.set("복사할 내용이 없습니다.")

    def select_random_preset(self):
        """랜덤으로 프리셋 선택"""
        if not self.presets:
            messagebox.showwarning("경고", "로드된 프리셋이 없습니다.")
            return

        random_preset = random.choice(self.presets)
        self.preset_var.set(random_preset['name'])
        self.on_preset_selected()
        self.status_var.set(f"랜덤 프리셋 '{random_preset['name']}' 선택됨")

    def get_selected_url(self):
        """선택된 URL 반환"""
        selection = self.url_tree.selection()
        if not selection:
            messagebox.showwarning("경고", "URL을 선택해주세요.")
            return None

        item = self.url_tree.item(selection[0])
        return item['values'][2]  # URL은 인덱스 2 (번호, 캡차, URL, 상태)

    def is_browser_alive(self):
        """브라우저가 아직 열려있는지 확인"""
        if not self.driver:
            return False
        try:
            # 브라우저 상태 확인 (창 핸들 가져오기 시도)
            self.driver.current_window_handle
            return True
        except:
            # 브라우저가 닫혔으면 driver 정리
            self.driver = None
            return False

    def open_browser(self):
        """Chrome 브라우저 열기"""
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("오류", "selenium이 설치되지 않았습니다.\npip install selenium 을 실행해주세요.")
            return

        # 브라우저가 이미 열려있고 유효한지 확인
        if self.is_browser_alive():
            return  # 이미 유효한 브라우저가 있음

        try:
            self.status_var.set("브라우저 시작 중...")
            self.root.update()

            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self.status_var.set("브라우저 준비 완료")
        except Exception as e:
            messagebox.showerror("오류", f"브라우저 시작 실패:\n{str(e)}\n\nChrome과 ChromeDriver가 설치되어 있는지 확인하세요.")
            self.driver = None

    def close_browser(self):
        """브라우저 닫기"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.status_var.set("브라우저 종료됨")

    def open_selected_url(self):
        """선택된 URL로 이동"""
        url = self.get_selected_url()
        if not url:
            return

        if not self.driver:
            self.open_browser()
            if not self.driver:
                return

        try:
            self.status_var.set(f"이동 중: {url}")
            self.root.update()
            self.driver.get(url)
            self.status_var.set(f"페이지 로드 완료: {url}")
        except Exception as e:
            messagebox.showerror("오류", f"페이지 이동 실패:\n{str(e)}")

    def on_url_double_click(self, event):
        """URL 더블클릭 시 해당 URL로 이동"""
        self.open_selected_url()

    def auto_fill(self):
        """선택된 URL에 자동 입력"""
        if not self.is_browser_alive():
            messagebox.showwarning("경고", "먼저 브라우저를 열고 URL로 이동해주세요.")
            return

        name = self.name_var.get()
        password = self.password_var.get()
        title = self.title_var.get()
        content = self.content_text.get("1.0", tk.END).strip()

        if not all([name, password, title, content]):
            messagebox.showwarning("경고", "이름, 비밀번호, 제목, 내용을 모두 입력해주세요.")
            return

        try:
            self.status_var.set("자동 입력 중...")
            self.root.update()

            wait = WebDriverWait(self.driver, 5)

            # 그누보드 글쓰기 양식 필드명들
            field_mappings = {
                'name': ['wr_name', 'name'],
                'password': ['wr_password', 'password'],
                'title': ['wr_subject', 'subject', 'title'],
                'content': ['wr_content', 'content']
            }

            # 이름 입력
            self.fill_field(field_mappings['name'], name)

            # 비밀번호 입력
            self.fill_field(field_mappings['password'], password)

            # 제목 입력
            self.fill_field(field_mappings['title'], title)

            # 내용 입력 (textarea 또는 에디터)
            self.fill_content(field_mappings['content'], content)

            # HTML 사용 체크박스 활성화
            self.enable_html_option()

            # 캡차 확인
            has_captcha = self.check_captcha_exists()

            if has_captcha:
                # 캡차가 있으면 상태만 표시 (수동 처리 필요)
                selection = self.url_tree.selection()
                if selection:
                    self.url_tree.set(selection[0], "상태", "캡차필요")
                self.status_var.set("캡차가 있습니다 - 수동으로 입력 후 등록해주세요")
            else:
                # 캡차가 없으면 바로 등록
                self.click_submit_button()
                selection = self.url_tree.selection()
                if selection:
                    self.url_tree.set(selection[0], "상태", "등록완료")
                self.status_var.set("자동 등록 완료")
        except Exception as e:
            self.status_var.set(f"자동 입력 실패: {str(e)}")
            messagebox.showerror("오류", f"자동 입력 실패:\n{str(e)}")

    def fill_field(self, field_names, value):
        """필드에 값 입력 - 다양한 방법으로 시도"""

        def try_fill_element(element, val):
            """요소에 값 입력 시도"""
            try:
                # 스크롤하여 요소가 보이게
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)

                # 요소가 상호작용 가능할 때까지 대기
                WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(element))

                element.clear()
                element.send_keys(val)
                return True
            except:
                pass

            # JavaScript로 직접 입력 시도
            try:
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, element, val)
                return True
            except:
                pass

            return False

        for field_name in field_names:
            # name 속성으로 찾기
            try:
                element = self.driver.find_element(By.NAME, field_name)
                if try_fill_element(element, value):
                    return True
            except NoSuchElementException:
                pass

            # id 속성으로 찾기
            try:
                element = self.driver.find_element(By.ID, field_name)
                if try_fill_element(element, value):
                    return True
            except NoSuchElementException:
                pass

        # 최후의 방법: JavaScript로 모든 가능한 필드에 직접 입력
        for field_name in field_names:
            try:
                result = self.driver.execute_script("""
                    var elem = document.querySelector('input[name="' + arguments[0] + '"], input[id="' + arguments[0] + '"], textarea[name="' + arguments[0] + '"], textarea[id="' + arguments[0] + '"]');
                    if (elem) {
                        elem.value = arguments[1];
                        elem.dispatchEvent(new Event('input', { bubbles: true }));
                        elem.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                """, field_name, value)
                if result:
                    return True
            except:
                pass

        return False

    def fill_content(self, field_names, content):
        """내용 필드에 값 입력 (에디터 지원) - 다양한 방법으로 시도"""

        def try_fill_textarea(element, text):
            """textarea에 값 입력 시도"""
            try:
                # 스크롤하여 요소가 보이게
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)

                # 요소가 상호작용 가능할 때까지 대기
                WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(element))

                element.clear()
                element.send_keys(text)
                return True
            except:
                pass

            # JavaScript로 직접 입력
            try:
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, element, text)
                return True
            except:
                pass

            return False

        # 먼저 일반 textarea 시도
        for field_name in field_names:
            try:
                element = self.driver.find_element(By.NAME, field_name)
                if try_fill_textarea(element, content):
                    return True
            except NoSuchElementException:
                continue

        # iframe 기반 에디터 시도 (CKEditor, SmartEditor 등)
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    body = self.driver.find_element(By.TAG_NAME, "body")

                    # 스크롤 및 클릭 가능 대기
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", body)
                        body.clear()
                        body.send_keys(content)
                        self.driver.switch_to.default_content()
                        return True
                    except:
                        # JavaScript로 직접 입력
                        try:
                            self.driver.execute_script("arguments[0].innerHTML = arguments[1];", body, content)
                            self.driver.switch_to.default_content()
                            return True
                        except:
                            pass

                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
        except:
            pass

        # JavaScript로 직접 입력 시도 (다양한 선택자)
        js_selectors = [
            'textarea[name="wr_content"]',
            'textarea[id="wr_content"]',
            'textarea[name="content"]',
            'textarea[id="content"]',
            'textarea',  # 첫 번째 textarea
        ]

        for selector in js_selectors:
            try:
                result = self.driver.execute_script("""
                    var elem = document.querySelector(arguments[0]);
                    if (elem) {
                        elem.value = arguments[1];
                        elem.dispatchEvent(new Event('input', { bubbles: true }));
                        elem.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                """, selector, content)
                if result:
                    return True
            except:
                pass

        # 에디터 API 직접 호출 시도 (CKEDITOR, SmartEditor 등)
        try:
            self.driver.execute_script("""
                // CKEditor
                if (typeof CKEDITOR !== 'undefined') {
                    for (var name in CKEDITOR.instances) {
                        CKEDITOR.instances[name].setData(arguments[0]);
                        return;
                    }
                }

                // SmartEditor (네이버)
                if (typeof oEditors !== 'undefined' && oEditors.length > 0) {
                    oEditors.getById['wr_content'].exec('UPDATE_CONTENTS_FIELD', []);
                    document.querySelector('textarea[name="wr_content"]').value = arguments[0];
                    return;
                }

                // TinyMCE
                if (typeof tinymce !== 'undefined') {
                    var editor = tinymce.activeEditor || tinymce.editors[0];
                    if (editor) {
                        editor.setContent(arguments[0]);
                        return;
                    }
                }
            """, content)
            return True
        except:
            pass

        return False

    def enable_html_option(self):
        """HTML 사용 옵션 활성화 - 다양한 방법으로 시도"""

        def handle_alert():
            """confirm 대화상자 처리 - 확인 클릭"""
            try:
                alert = WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                alert.accept()  # 확인 클릭
            except:
                pass

        def try_click_checkbox(element):
            """체크박스 클릭 시도 - 클릭 후 value도 설정"""
            try:
                if element and element.is_displayed():
                    if not element.is_selected():
                        # 스크롤하여 요소가 보이게
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.2)
                        element.click()
                        handle_alert()
                        # 클릭 후 value가 설정되었는지 확인하고, 안되어있으면 직접 설정
                        time.sleep(0.3)
                        try:
                            current_value = element.get_attribute("value")
                            if not current_value or current_value == "":
                                # value가 비어있으면 html1로 설정 (HTML 사용, 자동줄바꿈 없음)
                                self.driver.execute_script("arguments[0].value = 'html1';", element)
                        except:
                            pass
                    else:
                        # 이미 체크되어 있어도 value 확인
                        try:
                            current_value = element.get_attribute("value")
                            if not current_value or current_value == "":
                                self.driver.execute_script("arguments[0].value = 'html1';", element)
                        except:
                            pass
                    return True
            except:
                pass
            return False

        try:
            # 방법 1: id="html" 체크박스 (가장 흔한 형태)
            try:
                html_checkbox = self.driver.find_element(By.ID, "html")
                if try_click_checkbox(html_checkbox):
                    return True
            except NoSuchElementException:
                pass

            # 방법 2: name="html" 체크박스
            try:
                html_elem = self.driver.find_element(By.NAME, "html")
                if html_elem.get_attribute("type") == "checkbox":
                    if try_click_checkbox(html_elem):
                        return True
            except NoSuchElementException:
                pass

            # 방법 3: html1 라디오 버튼 (구버전 그누보드)
            try:
                html_radio = self.driver.find_element(By.ID, "html1")
                if try_click_checkbox(html_radio):
                    return True
            except NoSuchElementException:
                pass

            # 방법 4: name="html" 라디오 버튼 중 value="html1" 선택
            try:
                html_radios = self.driver.find_elements(By.NAME, "html")
                for radio in html_radios:
                    if radio.get_attribute("type") == "radio" and radio.get_attribute("value") == "html1":
                        if try_click_checkbox(radio):
                            return True
            except:
                pass

            # 방법 5: wr_html 체크박스
            try:
                wr_html = self.driver.find_element(By.NAME, "wr_html")
                if try_click_checkbox(wr_html):
                    return True
            except NoSuchElementException:
                pass

            # 방법 6: CSS 선택자로 다양한 HTML 관련 체크박스 찾기
            css_selectors = [
                'input[type="checkbox"][id*="html" i]',
                'input[type="checkbox"][name*="html" i]',
                'input[type="checkbox"][value*="html" i]',
                'input[id*="html" i]',
                'input[name*="html" i]',
            ]
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if try_click_checkbox(elem):
                            return True
                except:
                    pass

            # 방법 7: XPath로 "HTML" 텍스트 근처의 체크박스 찾기
            xpath_patterns = [
                '//label[contains(text(),"HTML")]/input[@type="checkbox"]',
                '//label[contains(text(),"HTML")]/preceding-sibling::input[@type="checkbox"]',
                '//label[contains(text(),"HTML")]/following-sibling::input[@type="checkbox"]',
                '//input[@type="checkbox"]/following-sibling::text()[contains(.,"HTML")]/preceding-sibling::input',
                '//*[contains(text(),"HTML")]/parent::*/input[@type="checkbox"]',
                '//*[contains(text(),"HTML")]/parent::*//input[@type="checkbox"]',
                '//input[@type="checkbox"][following-sibling::*[contains(text(),"HTML")]]',
                '//input[@type="checkbox"][preceding-sibling::*[contains(text(),"HTML")]]',
            ]
            for xpath in xpath_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        if try_click_checkbox(elem):
                            return True
                except:
                    pass

            # 방법 8: 라벨 클릭 (for 속성으로 연결된 경우)
            try:
                labels = self.driver.find_elements(By.XPATH, '//label[contains(text(),"HTML")]')
                for label in labels:
                    for_attr = label.get_attribute("for")
                    if for_attr:
                        try:
                            checkbox = self.driver.find_element(By.ID, for_attr)
                            if try_click_checkbox(checkbox):
                                return True
                        except:
                            pass
                    # 라벨 자체를 클릭
                    try:
                        label.click()
                        handle_alert()
                        return True
                    except:
                        pass
            except:
                pass

            # 방법 9: JavaScript로 다양한 방법 시도 (value도 반드시 설정)
            result = self.driver.execute_script("""
                // 체크박스를 찾아서 체크하고 value를 html1로 설정하는 함수
                function enableHtmlCheckbox(elem) {
                    if (!elem) return false;
                    elem.checked = true;
                    // 중요: value를 html1로 설정해야 서버에서 HTML로 인식함
                    // html1 = HTML 사용 (자동줄바꿈 없음)
                    // html2 = HTML 사용 (자동줄바꿈 있음)
                    if (!elem.value || elem.value === '') {
                        elem.value = 'html1';
                    }
                    elem.dispatchEvent(new Event('change', { bubbles: true }));
                    elem.dispatchEvent(new Event('click', { bubbles: true }));
                    return true;
                }

                // 1. id나 name에 html이 포함된 체크박스
                var selectors = [
                    'input[type="checkbox"][id="html"]',
                    'input[type="checkbox"][name="html"]',
                    'input#html',
                    'input[name="html"]',
                    'input[type="checkbox"][id*="html"]',
                    'input[type="checkbox"][name*="html"]',
                    'input[name="wr_html"]'
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elem = document.querySelector(selectors[i]);
                    if (elem) {
                        if (!elem.checked) {
                            enableHtmlCheckbox(elem);
                            return 'checked_and_value_set_' + i;
                        } else {
                            // 이미 체크되어 있어도 value 확인
                            if (!elem.value || elem.value === '') {
                                elem.value = 'html1';
                            }
                            return 'already_checked_value_ensured';
                        }
                    }
                }

                // 2. 라디오 버튼 형태
                var htmlRadio = document.getElementById('html1');
                if (htmlRadio && !htmlRadio.checked) {
                    htmlRadio.checked = true;
                    htmlRadio.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'radio_html1';
                }

                // 3. name="html" 라디오 버튼 중 value="html1"
                var htmlRadios = document.querySelectorAll('input[name="html"][type="radio"]');
                for (var j = 0; j < htmlRadios.length; j++) {
                    if (htmlRadios[j].value == 'html1' && !htmlRadios[j].checked) {
                        htmlRadios[j].checked = true;
                        htmlRadios[j].dispatchEvent(new Event('change', { bubbles: true }));
                        return 'radio_value_html1';
                    }
                }

                // 4. "HTML" 텍스트 근처의 체크박스 찾기
                var allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
                for (var k = 0; k < allCheckboxes.length; k++) {
                    var cb = allCheckboxes[k];
                    var parent = cb.parentElement;
                    if (parent && parent.textContent && parent.textContent.indexOf('HTML') !== -1) {
                        enableHtmlCheckbox(cb);
                        return 'found_near_html_text_value_set';
                    }
                }

                return 'not_found';
            """)

            if result and 'checked' in str(result):
                handle_alert()
                return True

            return False

        except Exception as e:
            # HTML 옵션 실패해도 계속 진행
            return False

    def check_captcha_exists(self):
        """캡차 존재 여부 확인"""
        try:
            captcha_selectors = [
                (By.ID, "captcha_img"),
                (By.CSS_SELECTOR, "img[src*='captcha']"),
                (By.CSS_SELECTOR, "img[src*='kcaptcha']"),
                (By.XPATH, "//img[contains(@src, 'captcha')]"),
            ]

            for by, selector in captcha_selectors:
                try:
                    captcha_img = self.driver.find_element(by, selector)
                    if captcha_img and captcha_img.is_displayed():
                        return True
                except NoSuchElementException:
                    continue

            return False
        except:
            return False

    def click_submit_button(self):
        """작성완료/등록 버튼 클릭"""
        try:
            submit_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), '작성완료')]"),
                (By.XPATH, "//button[contains(text(), '등록')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(@class, 'btn_submit')]"),
                (By.CSS_SELECTOR, ".btn_submit"),
            ]

            for by, selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(by, selector)
                    if submit_btn and submit_btn.is_displayed():
                        submit_btn.click()
                        time.sleep(1)  # 등록 후 잠시 대기
                        return True
                except NoSuchElementException:
                    continue

            return False
        except Exception as e:
            self.status_var.set(f"등록 버튼 클릭 실패: {str(e)}")
            return False

    def solve_captcha(self):
        """캡차 감지 및 수동 입력 요청"""
        try:
            # 캡차 이미지 찾기
            captcha_img = None
            captcha_selectors = [
                (By.ID, "captcha_img"),
                (By.CSS_SELECTOR, "img[src*='captcha']"),
                (By.CSS_SELECTOR, "img[src*='kcaptcha']"),
                (By.XPATH, "//img[contains(@src, 'captcha')]"),
            ]

            for by, selector in captcha_selectors:
                try:
                    captcha_img = self.driver.find_element(by, selector)
                    if captcha_img:
                        break
                except NoSuchElementException:
                    continue

            if not captcha_img:
                return True  # 캡차 없음, 성공으로 처리

            # 캡차 입력 필드 찾기
            captcha_input = None
            input_selectors = [
                (By.ID, "captcha_key"),
                (By.NAME, "captcha_key"),
                (By.NAME, "captcha"),
                (By.CSS_SELECTOR, "input[name*='captcha']"),
            ]

            for by, selector in input_selectors:
                try:
                    captcha_input = self.driver.find_element(by, selector)
                    if captcha_input:
                        break
                except NoSuchElementException:
                    continue

            if not captcha_input:
                return False

            # 캡차 입력 다이얼로그 표시
            self.status_var.set("캡차 입력 필요 - 브라우저에서 숫자 확인 후 입력하세요")
            self.root.update()

            # 사용자에게 캡차 입력 요청
            captcha_text = self.ask_captcha_input()

            if captcha_text:
                captcha_input.clear()
                captcha_input.send_keys(captcha_text)
                self.status_var.set(f"캡차 입력 완료: {captcha_text}")
                return True
            else:
                self.status_var.set("캡차 입력 취소됨")
                return False

        except Exception as e:
            self.status_var.set(f"캡차 처리 실패: {str(e)}")
            return False

    def ask_captcha_input(self):
        """캡차 입력 다이얼로그"""
        import tkinter.simpledialog as simpledialog

        # 브라우저 창을 앞으로 가져오기
        try:
            self.driver.switch_to.window(self.driver.current_window_handle)
        except:
            pass

        captcha_text = simpledialog.askstring(
            "캡차 입력",
            "브라우저에서 캡차 숫자를 확인하고 입력하세요:",
            parent=self.root
        )
        return captcha_text

    def one_click_run(self):
        """원클릭 실행: 브라우저 열기 -> URL 이동 -> 자동 입력"""
        url = self.get_selected_url()
        if not url:
            return

        # 입력값 확인
        name = self.name_var.get()
        password = self.password_var.get()
        title = self.title_var.get()
        content = self.content_text.get("1.0", tk.END).strip()

        if not all([name, password, title, content]):
            messagebox.showwarning("경고", "이름, 비밀번호, 제목, 내용을 모두 입력해주세요.")
            return

        # 브라우저가 없거나 닫혔으면 새로 열기
        if not self.is_browser_alive():
            self.open_browser()
            if not self.driver:
                return

        # URL로 이동
        try:
            self.status_var.set(f"이동 중: {url}")
            self.root.update()
            self.driver.get(url)

            # 페이지 로드 대기
            time.sleep(1.5)

            # 자동 입력
            self.auto_fill()

        except Exception as e:
            # 브라우저 관련 오류시 드라이버 정리
            if "no such window" in str(e) or "web view not found" in str(e):
                self.driver = None
                messagebox.showwarning("알림", "브라우저가 닫혔습니다. 다시 실행해주세요.")
            else:
                messagebox.showerror("오류", f"원클릭 실행 실패:\n{str(e)}")

    def register_all_presets(self):
        """선택된 URL에 모든 프리셋으로 등록"""
        url = self.get_selected_url()
        if not url:
            return

        # 프리셋 확인
        if not self.presets:
            messagebox.showwarning("경고", "로드된 프리셋이 없습니다.\n프리셋을 먼저 새로고침하세요.")
            return

        name = self.name_var.get()
        password = self.password_var.get()

        if not name or not password:
            messagebox.showwarning("경고", "이름과 비밀번호를 입력해주세요.")
            return

        # 확인 메시지
        if not messagebox.askyesno("확인", f"선택된 URL에 {len(self.presets)}개 프리셋을 모두 등록합니다.\n\nURL: {url}\n\n계속하시겠습니까?"):
            return

        # 프로그래스 다이얼로그 생성
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("모든 프리셋 등록 진행중")
        self.progress_window.geometry("450x150")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()  # 모달 창으로 설정
        self.progress_window.resizable(False, False)

        # 중앙 배치
        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 150) // 2
        self.progress_window.geometry(f"+{x}+{y}")

        ttk.Label(self.progress_window, text="모든 프리셋 등록 진행중...", font=("", 12)).pack(pady=10)

        self.progress_label = ttk.Label(self.progress_window, text="준비중...")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self.progress_window, length=400, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.progress_detail = ttk.Label(self.progress_window, text="")
        self.progress_detail.pack(pady=5)

        # 백그라운드에서 실행
        self.root.after(100, lambda: self.run_all_presets_register(url, name, password))

    def run_all_presets_register(self, url, name, password):
        """모든 프리셋 등록 실행"""
        # 브라우저 열기
        if not self.is_browser_alive():
            self.open_browser()
            if not self.driver:
                self.progress_window.destroy()
                return

        total = len(self.presets)
        success_count = 0
        fail_count = 0

        for i, preset in enumerate(self.presets):
            try:
                # 진행상황 업데이트
                self.progress_bar['value'] = (i / total) * 100
                self.progress_label.config(text=f"진행중: {i+1}/{total}")
                self.progress_detail.config(text=f"프리셋: {preset['name'][:30]}...")
                self.progress_window.update()

                # URL 이동
                self.driver.get(url)
                time.sleep(1.5)

                # 필드 입력
                field_mappings = {
                    'name': ['wr_name', 'name'],
                    'password': ['wr_password', 'password'],
                    'title': ['wr_subject', 'subject', 'title'],
                    'content': ['wr_content', 'content']
                }

                self.fill_field(field_mappings['name'], name)
                self.fill_field(field_mappings['password'], password)
                self.fill_field(field_mappings['title'], preset['title'])
                self.fill_content(field_mappings['content'], preset['content'])
                self.enable_html_option()

                # 등록 버튼 클릭
                if self.click_submit_button():
                    success_count += 1
                else:
                    fail_count += 1

                time.sleep(1)

            except Exception as e:
                fail_count += 1
                # 브라우저가 닫혔으면 중단
                if "no such window" in str(e) or "web view not found" in str(e):
                    self.driver = None
                    self.progress_window.destroy()
                    messagebox.showwarning("중단", f"브라우저가 닫혔습니다.\n\n성공: {success_count}개\n실패: {fail_count}개")
                    return

        # 완료
        self.progress_bar['value'] = 100
        self.progress_window.destroy()

        # 현재 선택된 항목 상태 업데이트
        selection = self.url_tree.selection()
        if selection:
            self.url_tree.set(selection[0], "상태", f"등록{success_count}개")

        # 완료 팝업
        messagebox.showinfo("완료", f"모든 프리셋 등록 완료!\n\n성공: {success_count}개\n실패: {fail_count}개\n총: {total}개")

    def auto_register_all_no_captcha(self):
        """캡차 없는 모든 사이트에 자동 등록"""
        # 입력값 확인
        name = self.name_var.get()
        password = self.password_var.get()
        title = self.title_var.get()
        content = self.content_text.get("1.0", tk.END).strip()

        if not all([name, password, title, content]):
            messagebox.showwarning("경고", "이름, 비밀번호, 제목, 내용을 모두 입력해주세요.\n프리셋을 먼저 선택하세요.")
            return

        # 캡차 없는 URL 필터링
        no_captcha_items = []
        for item in self.url_tree.get_children(''):
            values = self.url_tree.item(item)['values']
            captcha_mark = values[1]  # 캡차 열
            if captcha_mark == "" or captcha_mark != "✓":
                no_captcha_items.append((item, values[2]))  # (item_id, url)

        if not no_captcha_items:
            messagebox.showinfo("알림", "캡차 없는 사이트가 없습니다.")
            return

        # 확인 메시지
        if not messagebox.askyesno("확인", f"캡차 없는 {len(no_captcha_items)}개 사이트에 자동 등록합니다.\n계속하시겠습니까?"):
            return

        # 프로그래스 다이얼로그 생성
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("자동 등록 진행중")
        self.progress_window.geometry("400x150")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()  # 모달 창으로 설정
        self.progress_window.resizable(False, False)

        # 중앙 배치
        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 150) // 2
        self.progress_window.geometry(f"+{x}+{y}")

        ttk.Label(self.progress_window, text="자동 등록 진행중...", font=("", 12)).pack(pady=10)

        self.progress_label = ttk.Label(self.progress_window, text="준비중...")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self.progress_window, length=350, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.progress_detail = ttk.Label(self.progress_window, text="")
        self.progress_detail.pack(pady=5)

        # 백그라운드에서 실행
        self.root.after(100, lambda: self.run_auto_register(no_captcha_items))

    def run_auto_register(self, items):
        """자동 등록 실행 (5개씩 끊어서)"""
        # 브라우저 열기
        if not self.is_browser_alive():
            self.open_browser()
            if not self.driver:
                self.progress_window.destroy()
                return

        total = len(items)
        success_count = 0
        fail_count = 0
        batch_size = 5

        name = self.name_var.get()
        password = self.password_var.get()
        title = self.title_var.get()
        content = self.content_text.get("1.0", tk.END).strip()

        for i, (item_id, url) in enumerate(items):
            try:
                # 진행상황 업데이트
                self.progress_bar['value'] = (i / total) * 100
                self.progress_label.config(text=f"진행중: {i+1}/{total}")
                self.progress_detail.config(text=f"{url[:50]}...")
                self.progress_window.update()

                # URL 이동
                self.driver.get(url)
                time.sleep(1.5)

                # 필드 입력
                field_mappings = {
                    'name': ['wr_name', 'name'],
                    'password': ['wr_password', 'password'],
                    'title': ['wr_subject', 'subject', 'title'],
                    'content': ['wr_content', 'content']
                }

                self.fill_field(field_mappings['name'], name)
                self.fill_field(field_mappings['password'], password)
                self.fill_field(field_mappings['title'], title)
                self.fill_content(field_mappings['content'], content)
                self.enable_html_option()

                # 등록 버튼 클릭
                if self.click_submit_button():
                    self.url_tree.set(item_id, "상태", "등록완료")
                    success_count += 1
                else:
                    self.url_tree.set(item_id, "상태", "등록실패")
                    fail_count += 1

                time.sleep(1)

                # 5개마다 잠시 대기 (랙 방지)
                if (i + 1) % batch_size == 0 and i + 1 < total:
                    self.progress_detail.config(text="잠시 대기중... (서버 부하 방지)")
                    self.progress_window.update()
                    time.sleep(2)

            except Exception as e:
                self.url_tree.set(item_id, "상태", "오류")
                fail_count += 1

        # 완료
        self.progress_bar['value'] = 100
        self.progress_window.destroy()

        # 완료 팝업
        messagebox.showinfo("완료", f"자동 등록 완료!\n\n성공: {success_count}개\n실패: {fail_count}개\n총: {total}개")

    def on_closing(self):
        """프로그램 종료 시"""
        self.close_browser()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BacklinkAutoWriter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
