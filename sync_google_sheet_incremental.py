#!/usr/bin/env python3
"""
Google Sheets to sbdb Incremental Sync Script
구글 시트 데이터를 증분 업데이트로 sbdb에 저장하는 스크립트
"""

import gspread
from google.oauth2.service_account import Credentials
import subprocess
import json
import sys
import io
import hashlib
from datetime import datetime
from pathlib import Path

# Windows console UTF-8 encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If it fails, continue with default encoding

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

# 동기화 상태 로드
def load_sync_state():
    """sync_state.json에서 이전 동기화 상태 읽기"""
    state_path = Path(__file__).parent / "sync_state.json"

    if not state_path.exists():
        return {
            "last_sync": None,
            "synced_rows": {},
            "total_rows": 0
        }

    with open(state_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 동기화 상태 저장
def save_sync_state(state):
    """sync_state.json에 동기화 상태 저장"""
    state_path = Path(__file__).parent / "sync_state.json"

    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# 행 해시 생성 (고유 ID)
def generate_row_hash(row, headers):
    """행의 고유 ID 생성 (부서명 + 용역명)"""
    # 첫 두 컬럼(부서명, 용역명)으로 고유 ID 생성
    if len(headers) >= 2:
        key = f"{row.get(headers[0], '')}-{row.get(headers[1], '')}"
    else:
        # 모든 값을 결합
        key = "-".join(str(v) for v in row.values())

    return hashlib.md5(key.encode('utf-8')).hexdigest()

# 체크섬 생성 (내용 변경 감지)
def generate_checksum(row):
    """행 내용의 체크섬 생성"""
    content = json.dumps(row, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# 구글 시트 연결
def connect_to_sheet(config):
    """Service Account로 구글 시트에 연결"""
    service_account_file = Path(__file__).parent / config['service_account_file']

    if not service_account_file.exists():
        print(f"❌ Service Account JSON 파일을 찾을 수 없습니다.")
        print(f"   경로: {service_account_file}")
        sys.exit(1)

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    try:
        creds = Credentials.from_service_account_file(
            str(service_account_file),
            scopes=scopes
        )

        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config['sheet_id'])

        if 'gid' in config and config['gid']:
            for worksheet in spreadsheet.worksheets():
                if str(worksheet.id) == str(config['gid']):
                    return worksheet
            print(f"⚠️  GID {config['gid']}를 찾을 수 없어서 첫 번째 시트를 사용합니다.")

        return spreadsheet.sheet1

    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        sys.exit(1)

# 데이터 추출
def fetch_sheet_data(worksheet):
    """구글 시트에서 데이터 추출"""
    try:
        all_values = worksheet.get_all_values()

        if not all_values or len(all_values) < 3:
            print("⚠️  데이터가 충분하지 않습니다.")
            return [], []

        # 두 번째 행을 헤더로 사용
        raw_headers = all_values[1]

        # 빈 헤더 처리
        headers = []
        header_indices = []
        seen = set()

        for idx, header in enumerate(raw_headers):
            if not header or header.strip() == '':
                continue

            original_header = header.strip()
            unique_header = original_header
            counter = 1
            while unique_header in seen:
                unique_header = f"{original_header}_{counter}"
                counter += 1

            headers.append(unique_header)
            header_indices.append(idx)
            seen.add(unique_header)

        # 데이터 행 변환
        all_records = []
        for row in all_values[2:]:
            if not any(cell.strip() for cell in row if cell):
                continue

            record = {}
            for header, idx in zip(headers, header_indices):
                if idx < len(row):
                    record[header] = row[idx]
                else:
                    record[header] = ""

            # 용역명(두 번째 컬럼)이 비어있으면 건너뛰기
            if len(headers) > 1:
                project_name = record.get(headers[1], "").strip()
                if not project_name:
                    continue

            all_records.append(record)

        print(f"📊 전체 데이터: {len(all_records)}개 행")
        print(f"📋 컬럼 ({len(headers)}개): {', '.join(headers[:5])}" +
              (f", ..." if len(headers) > 5 else ""))

        return all_records, headers

    except Exception as e:
        print(f"❌ 데이터 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 변경 사항 감지
def detect_changes(current_data, headers, sync_state):
    """현재 데이터와 이전 상태 비교하여 변경 사항 감지"""
    changes = {
        'new': [],       # 새로 추가된 행
        'updated': [],   # 내용이 변경된 행
        'deleted': [],   # 삭제된 행
        'unchanged': 0   # 변경 없는 행
    }

    current_hashes = set()

    for idx, row in enumerate(current_data):
        row_hash = generate_row_hash(row, headers)
        checksum = generate_checksum(row)
        current_hashes.add(row_hash)

        if row_hash not in sync_state['synced_rows']:
            # 새 행
            changes['new'].append({
                'index': idx + 1,
                'hash': row_hash,
                'checksum': checksum,
                'data': row
            })
        else:
            # 기존 행 - 내용 변경 확인
            old_checksum = sync_state['synced_rows'][row_hash]['checksum']
            if checksum != old_checksum:
                changes['updated'].append({
                    'index': idx + 1,
                    'hash': row_hash,
                    'checksum': checksum,
                    'data': row,
                    'doc_id': sync_state['synced_rows'][row_hash]['doc_id']
                })
            else:
                changes['unchanged'] += 1

    # 삭제된 행 감지
    for old_hash, old_data in sync_state['synced_rows'].items():
        if old_hash not in current_hashes:
            changes['deleted'].append({
                'hash': old_hash,
                'title': old_data['title'],
                'doc_id': old_data['doc_id']
            })

    return changes

# sbdb에 문서 저장
def save_to_sbdb(row_data, headers, config, index):
    """한 행의 데이터를 sbdb에 저장"""
    # 부서명 (첫 번째 컬럼)
    department = row_data.get(headers[0], "").strip() if len(headers) > 0 else ""
    # 용역명 (두 번째 컬럼)
    project_name = row_data.get(headers[1], "").strip() if len(headers) > 1 else ""

    # 타이틀 생성: [입찰참여] 카테고리 + 부서명 + 용역명 (50자 제한)
    if department and project_name:
        title_base = f"{department} - {project_name}"
    elif department:
        title_base = department
    elif project_name:
        title_base = project_name
    else:
        title_base = "입찰정보"

    # 용역명이 너무 길면 50자로 자르기
    if len(title_base) > 50:
        title_base = title_base[:47] + "..."

    title = f"[입찰참여] {title_base} (#{index})"

    content_lines = [f"# {title}", ""]

    for header in headers:
        value = row_data.get(header, "")
        if value != "" and value is not None:
            content_lines.append(f"- **{header}**: {value}")

    content = "\n".join(content_lines)

    today = datetime.now().strftime("%Y.%m.%d")
    tags = config.get('tags', []) + [today, "입찰참여"]
    tags_str = ",".join(tags)

    sbdb_script = r"C:\Users\hjj\.claude\skills\sbdb\scripts\save_document.py"

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
            # 문서 ID 추출 (출력에서)
            doc_id = extract_doc_id(result.stdout)
            return True, doc_id, None
        else:
            return False, None, result.stderr

    except Exception as e:
        return False, None, str(e)

# sbdb 문서 업데이트
def update_sbdb_document(doc_id, row_data, headers, config, index):
    """sbdb의 기존 문서 업데이트"""
    # 부서명 (첫 번째 컬럼)
    department = row_data.get(headers[0], "").strip() if len(headers) > 0 else ""
    # 용역명 (두 번째 컬럼)
    project_name = row_data.get(headers[1], "").strip() if len(headers) > 1 else ""

    # 타이틀 생성: [입찰참여] 카테고리 + 부서명 + 용역명 (50자 제한)
    if department and project_name:
        title_base = f"{department} - {project_name}"
    elif department:
        title_base = department
    elif project_name:
        title_base = project_name
    else:
        title_base = "입찰정보"

    # 용역명이 너무 길면 50자로 자르기
    if len(title_base) > 50:
        title_base = title_base[:47] + "..."

    title = f"[입찰참여] {title_base} (#{index})"

    content_lines = [f"# {title}", ""]

    for header in headers:
        value = row_data.get(header, "")
        if value != "" and value is not None:
            content_lines.append(f"- **{header}**: {value}")

    content = "\n".join(content_lines)

    sbdb_script = r"C:\Users\hjj\.claude\skills\sbdb\scripts\update_document.py"

    cmd = [
        "python",
        sbdb_script,
        doc_id,
        "--content", content,
        "--title", title,
        "--regenerate-embedding"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        return result.returncode == 0, result.stderr if result.returncode != 0 else None

    except Exception as e:
        return False, str(e)

# sbdb 문서 삭제
def delete_sbdb_document(doc_id):
    """sbdb에서 문서 삭제"""
    sbdb_script = r"C:\Users\hjj\.claude\skills\sbdb\scripts\delete_document.py"

    cmd = [
        "python",
        sbdb_script,
        doc_id,
        "--confirm"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        return result.returncode == 0

    except Exception as e:
        return False

# 문서 ID 추출
def extract_doc_id(output):
    """save_document.py 출력에서 문서 ID 추출"""
    import re
    match = re.search(r'ID:\s*([a-f0-9-]+)', output)
    if match:
        return match.group(1)
    return None

# 메인 함수
def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🔄 Google Sheets → sbdb 증분 동기화")
    print("=" * 60)

    # 설정 로드
    print("\n📝 설정 파일 로드 중...")
    config = load_config()
    print(f"   시트 ID: {config['sheet_id']}")
    print(f"   DB 이름: {config.get('sbdb_db_name', 'company')}")

    # 동기화 상태 로드
    print("\n📂 이전 동기화 상태 로드 중...")
    sync_state = load_sync_state()

    if sync_state['last_sync']:
        last_sync_time = datetime.fromisoformat(sync_state['last_sync'])
        time_diff = datetime.now() - last_sync_time
        hours = int(time_diff.total_seconds() / 3600)
        minutes = int((time_diff.total_seconds() % 3600) / 60)

        print(f"   마지막 동기화: {sync_state['last_sync']}")
        print(f"   경과 시간: {hours}시간 {minutes}분 전")
        print(f"   이전 행 수: {sync_state['total_rows']}개")
    else:
        print("   ✨ 첫 동기화입니다!")

    # 구글 시트 연결
    print("\n🔗 구글 시트 연결 중...")
    worksheet = connect_to_sheet(config)
    print(f"   시트 이름: {worksheet.title}")

    # 데이터 추출
    print("\n📥 데이터 추출 중...")
    current_data, headers = fetch_sheet_data(worksheet)

    if not current_data:
        print("⚠️  데이터가 없습니다.")
        return

    # 변경 사항 감지
    print("\n🔍 변경 사항 감지 중...")
    changes = detect_changes(current_data, headers, sync_state)

    print(f"   ✨ 새 행: {len(changes['new'])}개")
    print(f"   🔄 수정된 행: {len(changes['updated'])}개")
    print(f"   🗑️ 삭제된 행: {len(changes['deleted'])}개")
    print(f"   ⏭️ 변경 없음: {changes['unchanged']}개")

    total_changes = len(changes['new']) + len(changes['updated']) + len(changes['deleted'])

    if total_changes == 0:
        print("\n✅ 변경 사항이 없습니다. 동기화를 건너뜁니다.")
        return

    # 변경 사항 처리
    print(f"\n💾 변경 사항 처리 중... (총 {total_changes}개)")

    success_count = 0
    fail_count = 0
    processed = 0

    # 새 행 추가
    for item in changes['new']:
        processed += 1
        success, doc_id, error = save_to_sbdb(item['data'], headers, config, item['index'])

        if success and doc_id:
            success_count += 1
            title_field = headers[0] if headers else "항목"
            title = f"{item['data'].get(title_field, '항목')} - #{item['index']}"

            # 상태 업데이트
            sync_state['synced_rows'][item['hash']] = {
                'row_number': item['index'],
                'title': title,
                'doc_id': doc_id,
                'checksum': item['checksum']
            }

            print(f"   ✅ [{processed}/{total_changes}] 새 행 추가: {title[:50]}...")
        else:
            fail_count += 1
            print(f"   ❌ [{processed}/{total_changes}] 추가 실패: {error}")

    # 기존 행 업데이트
    for item in changes['updated']:
        processed += 1
        success, error = update_sbdb_document(item['doc_id'], item['data'], headers, config, item['index'])

        if success:
            success_count += 1
            title_field = headers[0] if headers else "항목"
            title = f"{item['data'].get(title_field, '항목')} - #{item['index']}"

            # 상태 업데이트
            sync_state['synced_rows'][item['hash']]['checksum'] = item['checksum']
            sync_state['synced_rows'][item['hash']]['title'] = title

            print(f"   🔄 [{processed}/{total_changes}] 업데이트: {title[:50]}...")
        else:
            fail_count += 1
            print(f"   ❌ [{processed}/{total_changes}] 업데이트 실패: {error}")

    # 삭제된 행 제거
    for item in changes['deleted']:
        processed += 1
        success = delete_sbdb_document(item['doc_id'])

        if success:
            success_count += 1
            del sync_state['synced_rows'][item['hash']]
            print(f"   🗑️ [{processed}/{total_changes}] 삭제: {item['title'][:50]}...")
        else:
            fail_count += 1
            print(f"   ❌ [{processed}/{total_changes}] 삭제 실패")

    # 동기화 상태 저장
    sync_state['last_sync'] = datetime.now().isoformat()
    sync_state['total_rows'] = len(current_data)
    save_sync_state(sync_state)

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 증분 동기화 완료")
    print("=" * 60)
    print(f"   ✨ 추가: {len(changes['new'])}개")
    print(f"   🔄 수정: {len(changes['updated'])}개")
    print(f"   🗑️ 삭제: {len(changes['deleted'])}개")
    print(f"   ⏭️ 건너뛰기: {changes['unchanged']}개")
    print(f"   ✅ 성공: {success_count}개")
    print(f"   ❌ 실패: {fail_count}개")
    print("=" * 60)

if __name__ == "__main__":
    main()
