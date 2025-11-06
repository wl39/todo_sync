# todo_sync

# todo_sync 설계서 v0.1

## 0. 개요

* 목적: 간단한 투두를 달력 기반으로 관리하고, WebSocket으로 동일 유저 혹은 퍼블릭 페이지에서 실시간 동기화되는 웹앱을 구현한다.
* 기술 스택: Frontend는 React + TypeScript + Vite, UI는 MUI 최소 설치, Backend는 FastAPI + SQLAlchemy + Pydantic, DB는 MySQL, 실시간은 FastAPI WebSocket, 확장을 위해 Redis Pub/Sub 선택적 도입을 고려한다.
* 향후 확장: LangGraph 또는 AI Agent가 이벤트를 구독해 자동화/요약/추천을 수행할 수 있도록 설계한다.

## 1. 사용자 스토리

1. 사용자는 회원가입/로그인 후 투두를 생성한다.
2. 달력 왼쪽에 날짜별 해야 하는 투두 개수가 보인다.
3. 달력의 날짜를 클릭하면 오른쪽 패널에 해당 날짜의 투두 타이틀 목록이 보인다.
4. 타이틀을 클릭하면 아코디언으로 설명이 펼쳐진다.
5. 타이틀 왼쪽 체크박스를 클릭할 때마다 상태가 `PENDING → DONE → PARTIAL → PENDING` 순환한다.
6. 동일 계정으로 로그인된 모든 세션에서 WebSocket으로 변경 사항이 즉시 동기화된다.
7. 사용자는 자신의 캘린더를 Private/공개 보기/Public Edit 중에서 선택해 퍼블릭 URL을 공유할 수 있다.
8. 퍼블릭 페이지에서도 실시간으로 동기화되고, 설정에 따라 누구나 수정 가능하거나 편집 토큰이 있는 사람만 수정 가능하도록 할 수 있다.

## 2. 요구사항 정리

### 기능 요구사항

* 회원가입/로그인 및 JWT 인증을 제공한다.
* 투두는 `title`, `description`, `created_date`를 가진다.
* 달력에는 해야 하는 투두 수가 표시되며, `PENDING`과 `PARTIAL`만 카운트한다.
* 날짜 클릭 시 해당 날짜의 투두 목록을 우측에 표시한다.
* 체크박스 클릭으로 상태가 순환되며, 변경 사항은 실시간 동기화된다.
* 퍼블릭 공유: `private`, `public_view`, `public_edit` 모드를 제공한다.
* 퍼블릭 URL은 슬러그로 접근하며, `public_edit`의 편집 권한은 기본적으로 `edit_token`으로 보호한다.

### 비기능 요구사항

* 확장성: 다중 인스턴스 환경에서 Redis Pub/Sub를 통해 WS 브로드캐스트를 확장한다.
* 신뢰성: 낙관적 동시성 제어와 버전 필드를 이용해 경합을 처리한다.
* 보안: JWT, 비밀번호 해시, 퍼블릭 편집 시 레이트 리밋과 감사 로깅을 제공한다.
* 지역화/시간대: Asia/Seoul 기준 표현을 제공하되 DB에는 UTC 타임스탬프를 저장하고 `created_local_date`를 별도 필드로 유지한다.

## 3. 시스템 아키텍처

```
[React + TS + MUI]  ⇄  [FastAPI REST]  ⇄  [MySQL]
         │                 │
         └──── WebSocket ──┘
                         │
                    [Redis Pub/Sub]  (선택적, 다중 인스턴스)
```

* 채널 전략: `user:{user_id}`, `calendar:{public_slug}` 방을 운영한다.
* 이벤트는 REST 변화 시 서버가 브로드캐스트하며, 클라이언트는 캐시를 업데이트한다.

## 4. 데이터 모델 및 스키마

### 테이블: users

* `id` BIGINT PK, `email` VARCHAR UNIQUE, `password_hash` VARCHAR, `name` VARCHAR NULL
* `public_slug` VARCHAR UNIQUE, `share_mode` ENUM('private','public_view','public_edit') DEFAULT 'private'
* `edit_token` VARCHAR NULL UNIQUE
* `is_active` BOOL DEFAULT TRUE, `created_at` DATETIME(6) UTC, `updated_at` DATETIME(6) UTC, `last_login_at` DATETIME(6) UTC NULL

### 테이블: todos

* `id` BIGINT PK, `user_id` BIGINT FK(users.id)
* `title` VARCHAR(200), `description` TEXT
* `created_at` DATETIME(6) UTC, `updated_at` DATETIME(6) UTC
* `todo_local_date` DATE NOT NULL  // 달력에 사용할 날짜(Asia/Seoul 기준의 날짜 필드)
* `status` ENUM('PENDING','DONE','PARTIAL') DEFAULT 'PENDING'
* `version` INT DEFAULT 1, `is_deleted` BOOL DEFAULT FALSE
* 인덱스: (user_id, todo_local_date), (user_id, status, todo_local_date)

### 테이블: todo_audit

* `id` BIGINT PK, `todo_id` BIGINT FK(todos.id)
* `action` ENUM('CREATE','UPDATE','TOGGLE','DELETE')
* `from_status` ENUM(...) NULL, `to_status` ENUM(...) NULL
* `editor_user_id` BIGINT NULL, `editor_ip` VARCHAR(64) NULL
* `payload` JSON NULL, `created_at` DATETIME(6) UTC

### 4.5 마이그레이션 노트 (Alembic)

* 신규 컬럼 추가: `todo_local_date` (nullable=True로 추가 후 데이터 백필, 그 다음 NOT NULL로 변경)
* 백필 규칙: 기존 데이터는 `created_at AT TIME ZONE 'Asia/Seoul'`의 로컬 날짜로 채운다(혹은 모두 오늘 날짜로 일괄 설정 후 사용자가 수정할 수 있게 한다).
* 인덱스 생성: `(user_id, todo_local_date)`, `(user_id, status, todo_local_date)`
* 어플리케이션 레이어에서 `POST /todos`와 `PATCH /todos/{id}`는 반드시 `todo_date`를 수신해 `todo_local_date`에 저장한다.

예시 스니펫:

```py
# revision_xxxx_add_todo_date.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('todos', sa.Column('todo_local_date', sa.Date(), nullable=True))
    # TODO: backfill with created_at converted to Asia/Seoul date
    op.execute("""
        UPDATE todos
        SET todo_local_date = DATE(CONVERT_TZ(created_at, '+00:00', '+09:00'))
        WHERE todo_local_date IS NULL;
    """)
    op.alter_column('todos', 'todo_local_date', nullable=False)
    op.create_index('ix_todos_user_date', 'todos', ['user_id','todo_local_date'])
    op.create_index('ix_todos_user_status_date', 'todos', ['user_id','status','todo_local_date'])

def downgrade():
    op.drop_index('ix_todos_user_status_date', table_name='todos')
    op.drop_index('ix_todos_user_date', table_name='todos')
    op.drop_column('todos', 'todo_local_date')
```

## 5. API 설계

### 인증

* `POST /auth/register` → { email, password, name? } → 201
* `POST /auth/login` → { email, password } → { access_token }
* `GET /me` → 사용자 정보 반환

### 투두

* `GET /todos?date=YYYY-MM-DD` → 해당 날짜(`todo_local_date`)의 투두 목록을 반환한다.
* `POST /todos` → { title, description, todo_date }를 받아 생성한다.
* `PATCH /todos/{id}` → { title?, description?, status?, client_version } 부분 업데이트한다.
* `DELETE /todos/{id}` → 소프트 삭제한다.

### 달력 요약

* `GET /summary/month?month=YYYY-MM` → { 'YYYY-MM-01': 3, ... } 형식으로 `PENDING`+`PARTIAL` 수를 반환한다.

### 공유 설정

* `GET /sharing` → { share_mode, public_slug, has_edit_token }
* `PATCH /sharing` → { share_mode?, regen_edit_token?, open_edit_unprotected? } 설정한다.

### 퍼블릭 엔드포인트

* `GET /public/{slug}/todos?date=YYYY-MM-DD`
* `POST /public/{slug}/todos` (편집 권한 필요)
* `PATCH /public/{slug}/todos/{id}` (편집 권한 필요)
* 권한 체크: `public_view`는 읽기만, `public_edit`은 `edit_token` 요구가 기본이다.

### 예시 응답 스키마 (Pydantic)

```python
# All comments are in English by user's preference.
class TodoOut(BaseModel):
    id: int
    title: str
    description: str
    todo_local_date: date
    status: Literal['PENDING', 'DONE', 'PARTIAL']
    version: int
    updated_at: datetime
```

## 6. WebSocket 프로토콜

* 경로: `/ws`.
* 쿼리:

  * 인증 사용자: `?token=<JWT>`
  * 퍼블릭 구독: `?slug=<public_slug>`
  * 퍼블릭 편집: `?slug=<public_slug>&edit_token=<token>` 또는 서버 설정이 `open_edit_unprotected=true`인 경우 토큰 생략 가능하다.
* 서버는 연결 시 방을 자동 조인시킨다.
* 메시지 포맷

```json
{
  "type": "todo.updated",  // todo.created|todo.deleted|todo.toggled
  "data": { /* TodoOut */ },
  "meta": { "source_client_id": "uuid", "ts": 1730865612, "room": "user:42" }
}
```

* 에코 방지: 서버는 수신자의 `source_client_id`와 다를 때만 다시 보낸다.
* 다중 인스턴스: 로컬 브로드캐스트 후 Redis Pub/Sub로 동일 이벤트를 퍼블리시한다.

## 7. 동시성/일관성 전략

* 낙관적 잠금: `version` 필드로 갱신하며, `PATCH` 시 `WHERE id=? AND version=?`로 갱신한다.
* 상태 토글 쿼리 예시

```sql
UPDATE todos
SET status = CASE status
    WHEN 'PENDING' THEN 'DONE'
    WHEN 'DONE' THEN 'PARTIAL'
    ELSE 'PENDING'
  END,
  version = version + 1,
  updated_at = UTC_TIMESTAMP(6)
WHERE id = ? AND version = ?;
```

* 409 충돌 시 서버 버전을 반환하고 클라이언트는 캐시를 교정한다.

## 8. 권한과 보안

* JWT Bearer, 비밀번호는 bcrypt/argon2 해시를 사용한다.
* 퍼블릭 편집은 기본적으로 `edit_token` 요구로 설정한다.
* Rate limit: IP별 쓰기 요청에 대한 간단한 레이트 리밋을 둔다.
* 감사 로그: `todo_audit`에 모든 변경을 기록한다.

## 9. 프론트엔드 설계

### 라우팅

* `/app` 사설 앱, `/u/:slug` 퍼블릭 보기, `/u/:slug/edit?token=...` 퍼블릭 편집을 제공한다.

### 컴포넌트 트리

* `AppLayout` — 좌측 `CalendarPane`, 우측 `TodoListPane`로 구성한다.
* `CalendarPane` — `@mui/x-date-pickers/DateCalendar`의 `slots.day`를 커스터마이즈해 날짜 셀에 카운트를 배지로 렌더링한다.
* `TodoListPane` — `Accordion` 목록, 각 아이템은 `Checkbox` + `Typography(title)` + `AccordionDetails(description)`로 구성한다.

### 상태 관리

* 서버 상태: React Query를 사용한다.
* UI 상태: `selectedDate`, `isPublic`, `shareMode` 등은 Context/Zustand로 관리한다.
* 실시간: `useRealtime` 훅으로 WS 연결을 관리하고 React Query 캐시를 패치한다.

### 체크박스 순환 핸들러 (TS)

```ts
// All comments are in English by user's preference.
const nextStatus = (s: 'PENDING'|'DONE'|'PARTIAL') =>
  s === 'PENDING' ? 'DONE' : s === 'DONE' ? 'PARTIAL' : 'PENDING';

function onToggle(todo: Todo) {
  const updated = { ...todo, status: nextStatus(todo.status) };
  // optimistic update...
  // send PATCH; WS will reconcile with server version
}
```

### WebSocket 훅 스케치

```ts
// All comments are in English by user's preference.
function useRealtime(params: { token?: string; slug?: string; editToken?: string }) {
  // connect, keep source_client_id, merge incoming events into React Query cache
}
```

### MUI 최소 설치

* `@mui/material`, `@emotion/react`, `@emotion/styled`, `@mui/icons-material`, `@mui/x-date-pickers`만 설치한다.

## 10. 백엔드 구성

### 주요 패키지

* `fastapi`, `uvicorn[standard]`, `pydantic`, `sqlalchemy`, `alembic`, `PyMySQL`, `python-jose`(JWT), `passlib[bcrypt]`, `redis`(옵션)

### 디렉토리

```
backend/
  app/
    main.py
    api/
      auth.py
      todos.py
      public.py
      sharing.py
    models/
      user.py
      todo.py
    schemas/
      auth.py
      todo.py
      sharing.py
    services/
      auth.py
      todo.py
      ws.py
      broadcast.py
    core/
      config.py
      db.py
      security.py
    migrations/
```

### WebSocket 매니저 요약

* 연결 시 `user:{id}` 또는 `calendar:{slug}`로 join한다.
* REST 갱신 후 `broadcast.publish(Event)`를 호출한다.
* 단일 인스턴스는 인메모리 브로드캐스트, 다중 인스턴스는 Redis Pub/Sub를 사용한다.

## 11. 달력 요약 계산

* 월간 범위: `first_day..last_day`를 계산해 해당 월의 `PENDING`+`PARTIAL`을 `todo_local_date` 기준으로 날짜별 `COUNT(*)`로 그룹핑한다.
* 인덱스를 통해 `(user_id, status, todo_local_date)`로 빠르게 계산한다.

## 12. 배포/환경변수

* `.env`: `DATABASE_URL`, `JWT_SECRET`, `REDIS_URL?`, `EDIT_OPEN_UNPROTECTED=false`, `TZ=Asia/Seoul` 등을 사용한다.
* Docker Compose 예시: `mysql:8`, `backend`, `redis`(옵션), 프런트엔드는 정적 호스팅 또는 Nginx로 서빙한다.

## 13. 테스트 계획

* 단위: 서비스/리포지토리/권한 체크를 테스트한다.
* API: 인증, 투두 CRUD, 달력 요약, 퍼블릭 모드의 읽기/쓰기 경계 테스트를 수행한다.
* WS: 상태 토글 시 동일 사용자의 다중 세션 수신, 퍼블릭 페이지 브로드캐스트 수신을 검증한다.

## 14. AI Agent/LangGraph 고려사항

* 이벤트 훅: `todo.created/updated/toggled`를 큐로 밀어 `agent_queue`로 저장한다.
* Agent는 큐를 소비해 요약/우선순위/리마인드 제안 등을 생성한다.
* 스키마 초안: `agent_jobs(id, type, payload_json, status, created_at, updated_at)`를 둔다.

## 15. 빠른 스캐폴딩 가이드

### Frontend

```
pnpm create vite todo_sync --template react-ts
cd todo_sync
pnpm add @mui/material @emotion/react @emotion/styled @mui/icons-material @mui/x-date-pickers
pnpm add @tanstack/react-query
```

### Backend

```
uv venv && source .venv/bin/activate
pip install fastapi uvicorn[standard] pydantic sqlalchemy alembic PyMySQL python-jose passlib[bcrypt] redis
alembic init migrations
```

## 16. 기본 가정과 결정 사항

* 달력 카운트는 `PENDING`과 `PARTIAL`만 포함한다.
* 캘린더 공개 편집은 기본적으로 `edit_token`이 있어야 한다.
* 날짜 기준은 명세에 따라 `todo_date`를 사용한다.
* 타임존은 Asia/Seoul 기준으로 `created_local_date`를 별도 컬럼으로 보관해 필터/집계를 단순화한다.

## 17. 오픈 이슈 목록

* 완전 오픈 편집 모드가 필요한지 여부를 결정해야 한다.
* 생성일이 아닌 “예정일/기한” 개념이 필요하면 `due_local_date` 컬럼을 추가해야 한다.
* 퍼블릭 편집 남용 방지를 위해 CAPTCHA/레이트리밋/Write-Through 캐시 전략을 강화할지 결정해야 한다.
* 익명 편집자의 식별을 어떻게 남길지(`editor_ip`만으로 충분한지) 결정해야 한다.
* 삭제 권한과 소프트 삭제 복구 정책을 정의해야 한다.

## 18. MVP 커트라인

* 단일 인스턴스 + 인메모리 브로드캐스트로 시작한다.
* `public_view`만 먼저 제공 후 `public_edit`는 `edit_token` 방식으로 추가한다.
* Agent/LangGraph는 이벤트 훅/큐만 먼저 심고 비활성화한다.

## 19. API 예시

### 생성

```bash
curl -H "Authorization: Bearer <JWT>" -X POST /todos \
 -d '{"title":"Study","description":"Read 20 pages","todo_date":"2025-11-06"}'
```

### 월간 요약

```bash
curl -H "Authorization: Bearer <JWT>" \
 "/summary/month?month=2025-11"
```

---


