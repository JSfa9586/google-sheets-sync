#!/usr/bin/env python3
"""
구글시트 태그가 있는 모든 문서 삭제 스크립트
재동기화 전 기존 문서 정리용
"""

import subprocess
import json
import sys

def get_all_documents_with_tag(tag):
    """특정 태그가 있는 모든 문서 ID 조회"""
    cmd = [
        "python",
        r"C:\Users\hjj\.claude\skills\sbdb\scripts\list_documents.py",
        "--tag", tag,
        "--limit", "1000",  # 충분히 큰 수
        "--json"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode == 0:
            documents = json.loads(result.stdout)
            return [doc['id'] for doc in documents]
        else:
            print(f"문서 조회 실패: {result.stderr}")
            return []

    except Exception as e:
        print(f"오류 발생: {e}")
        return []

def delete_document(doc_id):
    """문서 삭제"""
    cmd = [
        "python",
        r"C:\Users\hjj\.claude\skills\sbdb\scripts\delete_document.py",
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description='구글시트 태그가 있는 모든 문서 삭제')
    parser.add_argument('--force', action='store_true', help='확인 없이 바로 삭제')
    args = parser.parse_args()

    tag = "구글시트"

    print("=" * 60)
    print("기존 문서 삭제 시작")
    print("=" * 60)

    # 1. 문서 ID 수집
    print(f"\n'{tag}' 태그가 있는 문서 조회 중...")
    doc_ids = get_all_documents_with_tag(tag)

    print(f"총 {len(doc_ids)}개 문서 발견")

    if not doc_ids:
        print("삭제할 문서가 없습니다.")
        return

    # 2. 삭제 확인
    if not args.force:
        confirm = input(f"\n정말로 {len(doc_ids)}개 문서를 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("삭제 취소됨")
            return
    else:
        print(f"\n--force 옵션: 확인 없이 {len(doc_ids)}개 문서 삭제를 시작합니다.")

    # 3. 문서 삭제
    print(f"\n문서 삭제 중...")
    success_count = 0
    fail_count = 0

    for idx, doc_id in enumerate(doc_ids):
        success = delete_document(doc_id)
        if success:
            success_count += 1
            print(f"  ✅ [{idx+1}/{len(doc_ids)}] 삭제 완료: {doc_id[:8]}...")
        else:
            fail_count += 1
            print(f"  ❌ [{idx+1}/{len(doc_ids)}] 삭제 실패: {doc_id[:8]}...")

    # 4. 결과 요약
    print("\n" + "=" * 60)
    print("삭제 완료")
    print("=" * 60)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {fail_count}개")
    print(f"📝 전체: {len(doc_ids)}개")
    print("=" * 60)

if __name__ == "__main__":
    main()
