#!/usr/bin/env python3
"""
Google Sheets to sbdb Sync Script
구글 시트 데이터를 자동으로 sbdb(Supabase Database)에 저장하는 스크립트
"""

import gspread
from google.oauth2.service_account import Credentials
import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path

# 설정 파일 로드
def load_config():
    """config.json 파일에서 설정 읽기"""
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        print("❌ config.json 파일을 찾을 수 없습니다.")
        print(f"   경로: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 구글 시트 인증 및 연결
def connect_to_sheet(config):
    """Service Account로 구글 시트에 연결"""
    service_account_file = Path(__file__).parent / config['service_account_file']

    if not service_account_file.exists():
        print(f"❌ Service Account JSON 파일을 찾을 수 없습니다.")
        print(f"   경로: {service_account_file}")
        sys.exit(1)

    # 인증 범위 설정
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    try:
        # 인증 정보 생성
        creds = Credentials.from_service_account_file(
            str(service_account_file),
            scopes=scopes
        )

        # gspread 클라이언트 생성
        client = gspread.authorize(creds)

        # 시트 열기
        spreadsheet = client.open_by_key(config['sheet_id'])

        # GID로 특정 워크시트 찾기 (선택사항)
        if 'gid' in config and config['gid']:
            # GID를 사용하여 시트 찾기
            for worksheet in spreadsheet.worksheets():
                if str(worksheet.id) == str(config['gid']):
                    return worksheet
            print(f"⚠️  GID {config['gid']}를 찾을 수 없어서 첫 번째 시트를 사용합니다.")

        # 첫 번째 워크시트 반환
        return spreadsheet.sheet1

    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        sys.exit(1)

# 데이터 추출
def fetch_sheet_data(worksheet, test_mode=False, test_limit=5):
    """구글 시트에서 데이터 추출"""
    try:
        # 모든 값을 가져오기
        all_values = worksheet.get_all_values()

        if not all_values or len(all_values) < 3:
            print("⚠️  데이터가 충분하지 않습니다.")
            return [], []

        # 두 번째 행을 헤더로 사용 (첫 행은 빈 행)
        raw_headers = all_values[1]

        # 빈 헤더 처리 및 중복 제거
        headers = []
        header_indices = []
        seen = set()

        for idx, header in enumerate(raw_headers):
            # 빈 헤더는 건너뛰기
            if not header or header.strip() == '':
                continue

            # 중복 헤더 처리 (번호 추가)
            original_header = header.strip()
            unique_header = original_header
            counter = 1
            while unique_header in seen:
                unique_header = f"{original_header}_{counter}"
                counter += 1

            headers.append(unique_header)
            header_indices.append(idx)
            seen.add(unique_header)

        # 데이터 행들을 딕셔너리 리스트로 변환
        all_records = []
        for row in all_values[2:]:  # 첫 행(빈 행) + 헤더 제외, 세 번째 행부터 데이터
            # 빈 행 건너뛰기
            if not any(cell.strip() for cell in row if cell):
                continue

            record = {}
            for header, idx in zip(headers, header_indices):
                # 인덱스가 row 길이를 넘지 않도록 확인
                if idx < len(row):
                    record[header] = row[idx]
                else:
                    record[header] = ""

            all_records.append(record)

        # 테스트 모드 또는 전체 모드
        if test_mode:
            data = all_records[:test_limit]
            print(f"📊 테스트 모드: {len(data)}개 행 추출 (전체: {len(all_records)}개)")
        else:
            data = all_records
            print(f"📊 전체 데이터 추출: {len(data)}개 행")

        # 헤더 정보 출력
        if headers:
            print(f"📋 컬럼 ({len(headers)}개): {', '.join(headers[:5])}" +
                  (f", ..." if len(headers) > 5 else ""))

        return data, headers

    except Exception as e:
        print(f"❌ 데이터 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# sbdb에 문서 저장
def save_to_sbdb(row_data, headers, config, index):
    """한 행의 데이터를 sbdb에 저장"""

    # 제목 생성 (첫 번째 컬럼 사용 또는 자동 생성)
    title_field = headers[0] if headers else "항목"
    title = f"{row_data.get(title_field, '항목')} - #{index+1}"

    # 문서 내용 생성 (Markdown 형식)
    content_lines = [f"# {title}", ""]

    for header in headers:
        value = row_data.get(header, "")
        if value != "" and value is not None:  # 빈 값 제외
            content_lines.append(f"- **{header}**: {value}")

    content = "\n".join(content_lines)

    # 태그 생성
    today = datetime.now().strftime("%Y.%m.%d")
    tags = config.get('tags', []) + [today]
    tags_str = ",".join(tags)

    # sbdb save_document.py 스크립트 경로
    sbdb_script = r"C:\Users\hjj\.claude\skills\sbdb\scripts\save_document.py"

    # sbdb 저장 명령 실행
    cmd = [
        "python",
        sbdb_script,
        "--content", content,
        "--title", title,
        "--tags", tags_str,
        "--db-name", config.get('sbdb_db_name', 'company'),
        "--type", "text"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr

    except Exception as e:
        return False, str(e)

# 메인 함수
def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 Google Sheets → sbdb 동기화 시작")
    print("=" * 60)

    # 명령행 인수 확인
    test_mode = "--test" in sys.argv

    # 설정 로드
    print("\n📝 설정 파일 로드 중...")
    config = load_config()
    print(f"   시트 ID: {config['sheet_id']}")
    print(f"   DB 이름: {config.get('sbdb_db_name', 'company')}")

    # 구글 시트 연결
    print("\n🔗 구글 시트 연결 중...")
    worksheet = connect_to_sheet(config)
    print(f"   시트 이름: {worksheet.title}")

    # 데이터 추출
    print("\n📥 데이터 추출 중...")
    data, headers = fetch_sheet_data(worksheet, test_mode=test_mode)

    if not data:
        print("⚠️  데이터가 없습니다.")
        return

    # sbdb에 저장
    print(f"\n💾 sbdb에 저장 중...")
    success_count = 0
    fail_count = 0

    for idx, row in enumerate(data):
        success, error = save_to_sbdb(row, headers, config, idx)

        if success:
            success_count += 1
            print(f"   ✅ [{idx+1}/{len(data)}] 저장 성공")
        else:
            fail_count += 1
            print(f"   ❌ [{idx+1}/{len(data)}] 저장 실패: {error}")

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 동기화 완료")
    print("=" * 60)
    print(f"   ✅ 성공: {success_count}개")
    print(f"   ❌ 실패: {fail_count}개")
    print(f"   📝 전체: {len(data)}개")
    print("=" * 60)

    if test_mode:
        print("\n💡 테스트 모드로 실행되었습니다.")
        print("   전체 동기화를 하려면: python sync_google_sheet.py")

if __name__ == "__main__":
    main()
