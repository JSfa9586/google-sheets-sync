#!/usr/bin/env python3
"""중복 문서 확인 스크립트"""

import subprocess
import json

def main():
    # 문서 목록 조회
    cmd = [
        "python",
        r"C:\Users\hjj\.claude\skills\sbdb\scripts\list_documents.py",
        "--tag", "입찰참여",
        "--json",
        "--limit", "500"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    if result.returncode != 0:
        print(f"오류: {result.stderr}")
        return

    try:
        docs = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print(f"출력: {result.stdout[:500]}")
        return

    titles = [doc['title'] for doc in docs]

    print(f"전체 문서: {len(titles)}개")
    print(f"고유 문서: {len(set(titles))}개")
    print(f"중복 문서: {len(titles) - len(set(titles))}개")

    # 중복된 타이틀 찾기
    title_counts = {}
    for title in titles:
        title_counts[title] = title_counts.get(title, 0) + 1

    duplicates = {title: count for title, count in title_counts.items() if count > 1}

    if duplicates:
        print(f"\n중복된 타이틀 ({len(duplicates)}개):")
        for title, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - [{count}회] {title[:80]}")

if __name__ == "__main__":
    main()
