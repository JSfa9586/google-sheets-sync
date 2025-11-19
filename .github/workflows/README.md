# GitHub Actions 자동화 설정

GitHub Actions를 사용하면 로컬 컴퓨터가 꺼져있어도 클라우드에서 자동 동기화가 실행됩니다.

## 장점

- ✅ 데스크탑이 꺼져있어도 동작
- ✅ 무료 (public repo 무제한, private repo 월 2000분)
- ✅ 로그 자동 저장
- ✅ 실패 시 이메일 알림
- ✅ 수동 실행 가능
- ✅ cron 스케줄 설정 가능

## 설정 방법

### 1. GitHub Repository 생성

```bash
# 로컬 디렉토리를 Git repository로 초기화
cd "C:\AI\놀이터"
git init
git add .
git commit -m "Initial commit: Google Sheets sync"

# GitHub에 repository 생성 후
git remote add origin https://github.com/YOUR_USERNAME/google-sheets-sync.git
git branch -M main
git push -u origin main
```

### 2. GitHub Secrets 설정

Repository Settings → Secrets and variables → Actions → New repository secret

다음 Secrets를 추가하세요:

#### `GOOGLE_SERVICE_ACCOUNT_JSON`
Service Account JSON 파일 전체 내용:
```bash
cat gen-lang-client-0556505482-9494678fbd1f.json
```
전체 JSON 내용을 복사하여 붙여넣기

#### `SHEET_ID`
```
1njmYSFNWwd4HIlE6HUtx-PZQGSB3SlEntui-53bRnu4
```

#### `GID`
```
1992781324
```

#### `SBDB_DB_NAME`
```
company
```

#### `SUPABASE_URL`
```bash
# sbdb 설정 파일에서 확인
cat ~/.claude/skills/sbdb/.env
```
예: `https://uouhocnkzepzsqdzvunn.supabase.co`

#### `SUPABASE_KEY`
```bash
# sbdb 설정 파일에서 확인
cat ~/.claude/skills/sbdb/.env
```
Supabase API 키 (anon 또는 service_role 키)

#### `OPENAI_API_KEY`
```bash
# sbdb 설정 파일에서 확인
cat ~/.claude/skills/sbdb/.env
```
OpenAI API 키

### 3. Workflow 활성화

1. GitHub repository 페이지로 이동
2. "Actions" 탭 클릭
3. "I understand my workflows, go ahead and enable them" 클릭

### 4. 수동 실행 테스트

1. Actions 탭 → "Google Sheets to Supabase Auto Sync" 선택
2. "Run workflow" 버튼 클릭
3. "Run workflow" 확인
4. 실행 로그 확인

## 스케줄 설정

현재 설정: **3시간마다 실행** (UTC 기준)

```yaml
schedule:
  - cron: '0 */3 * * *'
```

### 다른 스케줄 예시:

```yaml
# 매시간 실행
- cron: '0 * * * *'

# 매일 오전 9시 (KST = UTC+9, UTC 0시)
- cron: '0 0 * * *'

# 매주 월요일 오전 9시 (UTC 0시)
- cron: '0 0 * * 1'

# 6시간마다
- cron: '0 */6 * * *'

# 매일 오전 9시, 오후 3시, 오후 9시 (UTC 0시, 6시, 12시)
- cron: '0 0,6,12 * * *'
```

## 모니터링

### 실행 로그 확인
1. GitHub repository → Actions 탭
2. 최근 workflow 실행 클릭
3. "sync" job 클릭하여 상세 로그 확인

### 이메일 알림 설정
1. GitHub Settings → Notifications
2. "Actions" 섹션에서 "Send notifications for failed workflows only" 체크

## 문제 해결

### Secrets 확인
```bash
# GitHub CLI 설치 후
gh secret list
```

### Workflow 재실행
Actions 탭 → 실패한 workflow → "Re-run all jobs"

### 로그 다운로드
Actions 탭 → Workflow 실행 → 우측 상단 "..." → "Download log archive"

## sync_state.json 관리

GitHub Actions는 매 실행마다 깨끗한 환경에서 시작하므로, `sync_state.json` 파일을 보존해야 합니다.

### 방법 1: Artifacts 사용 (현재 설정)

Workflow가 `sync_state.json`을 artifact로 업로드하고, 다음 실행 시 다운로드합니다.

### 방법 2: Git에 커밋 (추가 가능)

```yaml
- name: Commit sync state
  run: |
    git config user.name github-actions
    git config user.email github-actions@github.com
    git add sync_state.json
    git diff --quiet && git diff --staged --quiet || git commit -m "Update sync state"
    git push
```

## 비용

- **GitHub Actions**: Public repo 무제한, Private repo 월 2000분 무료
- **OpenAI API**: ~$0.02/1M 토큰 (임베딩)
- **Supabase**: 무료 티어 충분

## Windows Task Scheduler vs GitHub Actions

| 항목 | Windows Task Scheduler | GitHub Actions |
|------|----------------------|----------------|
| 비용 | 무료 | 무료 (제한 내) |
| 데스크탑 꺼짐 | ❌ 동작 안함 | ✅ 동작함 |
| 로그 관리 | 수동 | 자동 |
| 알림 | 없음 | 이메일 |
| 설정 복잡도 | 낮음 | 중간 |

## 권장 사항

**두 가지 모두 사용**하는 것을 추천합니다:

- **Windows Task Scheduler**: 빠른 로컬 동기화 (1시간마다)
- **GitHub Actions**: 백업 동기화 (6시간마다)

이렇게 하면 데스크탑이 켜져있을 때는 빠르게 동기화되고, 꺼져있을 때도 GitHub Actions가 백업 역할을 합니다.
