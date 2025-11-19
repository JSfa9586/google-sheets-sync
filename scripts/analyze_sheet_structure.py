#!/usr/bin/env python3
"""
구글 시트 데이터 구조 분석 스크립트
"""

import gspread
from google.oauth2.service_account import Credentials
import json

# 설정 파일 로드
with open("config.json", 'r', encoding='utf-8') as f:
    config = json.load(f)

# 인증
scopes = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

creds = Credentials.from_service_account_file(
    config['service_account_file'],
    scopes=scopes
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(config['sheet_id'])

# GID로 워크시트 찾기
worksheet = None
for ws in spreadsheet.worksheets():
    if str(ws.id) == str(config['gid']):
        worksheet = ws
        break

if not worksheet:
    worksheet = spreadsheet.sheet1

print(f"시트 이름: {worksheet.title}")
print(f"=" * 60)

# 모든 값 가져오기
all_values = worksheet.get_all_values()

print(f"\n총 행 수: {len(all_values)}")
print(f"=" * 60)

# 헤더 (첫 행)
if all_values:
    headers = all_values[0]
    print(f"\n헤더 ({len(headers)}개 컬럼):")
    for idx, header in enumerate(headers):
        print(f"  [{idx}] {repr(header)}")

# 첫 3개 데이터 행 샘플
print(f"\n샘플 데이터 (첫 3개 행):")
print(f"=" * 60)
for i in range(1, min(4, len(all_values))):
    print(f"\n행 {i}:")
    for idx, (header, value) in enumerate(zip(headers, all_values[i])):
        if value:  # 빈 값이 아닐 때만 출력
            print(f"  [{idx}] {header}: {repr(value)}")
