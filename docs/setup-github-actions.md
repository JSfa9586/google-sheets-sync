# GitHub Actions 설정 가이드

## 빠른 설정 (5분 완료)

### 1단계: GitHub Repository 생성

```bash
cd "C:\AI\놀이터"

# Git 초기화 (아직 안했다면)
git init

# 불필요한 파일 제외
cat > .gitignore << 'EOF'
*.log
logs/
sync_state.json
config.json
gen-lang-client-*.json
*.pyc
__pycache__/
EOF

# 커밋
git add .
git commit -m "Add Google Sheets sync automation"

# GitHub에 push (repository 생성 후)
# https://github.com/new 에서 repository 생성
git remote add origin https://github.com/YOUR_USERNAME/google-sheets-sync.git
git branch -M main
git push -u origin main
```

### 2단계: GitHub Secrets 추가

Repository → Settings → Secrets and variables → Actions → New repository secret

#### 필수 Secrets:

1. **GOOGLE_SERVICE_ACCOUNT_JSON**
   ```bash
   cat gen-lang-client-0556505482-9494678fbd1f.json
   ```
   → 전체 JSON 복사하여 붙여넣기

2. **SHEET_ID**: `1njmYSFNWwd4HIlE6HUtx-PZQGSB3SlEntui-53bRnu4`

3. **GID**: `1992781324`

4. **SBDB_DB_NAME**: `company`

5. **SUPABASE_URL**:
   ```bash
   cat ~/.claude/skills/sbdb/.env | grep SUPABASE_URL
   ```

6. **SUPABASE_KEY**:
   ```bash
   cat ~/.claude/skills/sbdb/.env | grep SUPABASE_KEY
   ```

7. **OPENAI_API_KEY**:
   ```bash
   cat ~/.claude/skills/sbdb/.env | grep OPENAI_API_KEY
   ```

### 3단계: Workflow 활성화 및 테스트

1. GitHub repository → Actions 탭
2. "I understand my workflows, go ahead and enable them" 클릭
3. "Google Sheets to Supabase Auto Sync" 선택
4. "Run workflow" 클릭하여 수동 실행
5. 로그 확인하여 정상 동작 확인

### 4단계: 완료! 🎉

이제 3시간마다 자동으로 동기화됩니다. 데스크탑이 꺼져있어도 동작합니다!

## 스케줄 변경

`.github/workflows/sync-google-sheets.yml` 파일 수정:

```yaml
schedule:
  # 6시간마다로 변경
  - cron: '0 */6 * * *'
```

변경 후:
```bash
git add .github/workflows/sync-google-sheets.yml
git commit -m "Change sync schedule to 6 hours"
git push
```

## 모니터링

- **실행 기록**: GitHub → Actions 탭
- **이메일 알림**: Settings → Notifications → Actions
- **Slack 알림**: Slack webhook 추가 가능

## 문제 해결

### Q: Workflow가 실행되지 않아요
**A**: Actions 탭에서 "Enable workflows" 버튼 클릭

### Q: Secrets를 잘못 입력했어요
**A**: Settings → Secrets → 해당 Secret → Update

### Q: 더 자주 실행하고 싶어요
**A**: cron 스케줄 수정 (최소 5분 간격 권장)

### Q: Private repository인데 비용이 걱정돼요
**A**:
- Public으로 변경 (민감 정보는 Secrets에만)
- 또는 월 2000분 무료 사용
- 1회 실행 ~2분 소요 = 월 ~1000회 무료

## 보안 주의사항

✅ **안전함:**
- Service Account JSON은 Secret으로 저장
- Workflow 실행 후 자동 삭제
- 로그에 민감 정보 출력 안함

❌ **절대 하지 마세요:**
- Secret을 코드에 직접 작성
- Service Account JSON을 git에 커밋
- API 키를 로그에 출력

## 다음 단계

1. **알림 설정**: 실패 시 이메일 또는 Slack 알림
2. **로그 분석**: 동기화 통계 수집
3. **다중 시트**: 여러 Google Sheets 동기화
4. **백업**: Supabase 데이터 주기적 백업
