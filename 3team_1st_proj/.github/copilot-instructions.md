# 프로젝트 Copilot 규칙

## DB 스키마 동결

**`dbscript.sql` 은 수정 금지.**

이 파일은 확정된 ERD 상태를 그대로 반영한 SQL 스크립트다.
스키마 변경이 필요하다면 ERD를 먼저 재확정하고 팀 합의를 거쳐야 한다.

금지 사항:
- `dbscript.sql` 에 컬럼·테이블·제약을 추가·수정·삭제하지 않는다.
- `db.py`의 `init_table()` 내 `CREATE TABLE` DDL도 `dbscript.sql` 과 항상 동일하게 유지한다.
- 새로운 기능 구현 목적으로 DB 컬럼을 임의로 추가하지 않는다.
