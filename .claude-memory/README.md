# Claude Memory Sync

Claude Code의 프로젝트 메모리를 git으로 동기화하는 폴더.

## 왜 필요한가

Claude의 메모리는 기본적으로 `~/.claude/projects/<프로젝트>/memory/` (유저 홈)에 저장되어 git 추적 밖이다. 다른 PC에서 작업 이어가면 Claude는 프로젝트 맥락을 잊는다. 이 폴더가 해결책 — 메모리를 git에 박아 PC간 동기화.

## 동기화 방향

```
Claude 메모리 (유저 홈)  ←→  .claude-memory/ (이 폴더, git 추적)
```

## 사용법

### 메모리 → git에 반영 (push 방향)

작업 중 Claude가 새 메모리 생성/수정했을 때, 또는 다른 PC 가기 전:

**Windows (PowerShell):**
```powershell
Copy-Item -Force "$env:USERPROFILE\.claude\projects\d--Free-Vue\memory\*.md" "D:\Free_Vue\OCR\.claude-memory\"
cd D:\Free_Vue\OCR
git add .claude-memory/
git commit -m "sync Claude memory"
git push
```

**Linux/macOS:**
```bash
cp -f ~/.claude/projects/d--Free-Vue/memory/*.md ./.claude-memory/
git add .claude-memory/
git commit -m "sync Claude memory"
git push
```

### git → Claude 메모리에 반영 (pull 방향)

다른 PC에서 git pull 받은 후, Claude가 인식하도록:

**Windows (PowerShell):**
```powershell
git pull
mkdir -Force "$env:USERPROFILE\.claude\projects\d--Free-Vue\memory" | Out-Null
Copy-Item -Force "D:\Free_Vue\OCR\.claude-memory\*.md" "$env:USERPROFILE\.claude\projects\d--Free-Vue\memory\"
```

**Linux/macOS:**
```bash
git pull
mkdir -p ~/.claude/projects/d--Free-Vue/memory
cp -f ./.claude-memory/*.md ~/.claude/projects/d--Free-Vue/memory/
```

## 자동화 스크립트

- `sync-to-git.sh` (또는 `.ps1`): 메모리 → git 폴더 복사 (commit/push는 수동)
- `sync-from-git.sh` (또는 `.ps1`): git 폴더 → 메모리 복사

## 주의사항

- **민감정보 금지**: 비밀번호, API 키, 개인정보 등은 메모리에 저장 X. 이 폴더는 git에 올라가 공유됨.
- **충돌 방지**: 동시에 두 PC에서 메모리 편집 → git merge conflict 발생 가능. 한 PC에서 작업 후 push, 다른 PC에선 pull 후 작업.
- **MEMORY.md 인덱스 동기화**: 새 메모리 추가하면 `MEMORY.md` 인덱스도 같이 업데이트되어야 함 (Claude가 자동으로 해줌).
