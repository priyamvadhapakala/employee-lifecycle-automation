# Data dictionary and relational design (Phase 2)

All IDs are immutable text identifiers. Dates use ISO 8601 calendar dates (`YYYY-MM-DD`); timestamps use UTC ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). Monetary values are not currently modeled. `NOT NULL` means required; `NULL` means optional or not yet applicable. SQLite stores dates as text and checks ordering lexicographically, which is valid for these normalized formats. Allowed values below match the SQL `CHECK` constraints where listed.

## Entities and fields

### Department

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| department_id | TEXT | PK, required | `DEPT-NNN`; immutable | One department has many employees |
| department_name | TEXT | required, unique | Non-empty organizational name | — |
| cost_center | TEXT | required, unique | Stable cost center code | — |
| created_at | TEXT | required | UTC timestamp | — |

### Role

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| role_id | TEXT | PK, required | `ROLE-NNN`; immutable | One role has many employees |
| role_name | TEXT | required, unique | Non-empty job title | — |
| role_family | TEXT | required | Non-empty role grouping | — |
| employment_type_default | TEXT | required | `full_time`, `contractor` | — |
| created_at | TEXT | required | UTC timestamp | — |

### Manager

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| manager_id | TEXT | PK, required | `MGR-NNN`; immutable | One manager record has many employee reports |
| employee_id | TEXT | FK, required, unique | Employee acting as manager | References Employee; each manager record belongs to one employee |
| active_from | TEXT | required | ISO date | — |
| active_to | TEXT | optional | ISO date >= active_from | Null means current assignment |

### Employee

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| employee_id | TEXT | PK, required | `EMP-NNNNNN`; immutable | Parent for cases, grants and asset assignments |
| first_name, last_name | TEXT | required | Non-empty synthetic names | — |
| email | TEXT | required, unique | Synthetic email address | — |
| department_id | TEXT | FK, required | Existing Department | Department has many employees |
| role_id | TEXT | FK, required | Existing Role | Role has many employees |
| manager_id | TEXT | FK, optional | Existing Manager | Manager has many direct reports; nullable for top-level staff |
| employment_type | TEXT | required | `full_time`, `contractor` | — |
| employment_status | TEXT | required | `pending`, `active`, `completed`, `terminated` | — |
| hire_date, planned_start_date | TEXT | required | ISO dates; generator will check sensible order | — |
| actual_start_date, termination_date | TEXT | optional | ISO dates; actual start and termination cannot precede hire date | — |
| location | TEXT | required | Synthetic office/remote location label | — |
| created_at | TEXT | required | UTC timestamp | — |

### OnboardingCase

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| onboarding_case_id | TEXT | PK, required | `ONB-YYYY-NNNNNN`; immutable | Parent of onboarding tasks |
| employee_id | TEXT | FK, required, unique | One onboarding case per employee | Employee has zero or one onboarding case |
| opened_at | TEXT | required | UTC timestamp | — |
| planned_start_date | TEXT | required | ISO date | — |
| actual_start_date | TEXT | optional | ISO date >= case opening date | — |
| status | TEXT | required | `planned`, `in_progress`, `blocked`, `completed`, `cancelled` | — |
| completed_at | TEXT | optional | UTC timestamp >= opened_at | — |

### Task

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| task_id | TEXT | PK, required | `TASK-ONB-YYYY-NNNNNN-NNN` or `TASK-OFF-YYYY-NNNNNN-NNN`; immutable | Parent in dependency relationships |
| onboarding_case_id | TEXT | FK, optional | Existing onboarding case | Each task must reference exactly one case type |
| offboarding_case_id | TEXT | FK, optional | Existing offboarding case | Each task must reference exactly one case type |
| task_type | TEXT | required | Named workflow action | — |
| owner_team | TEXT | required | `HR`, `IT`, `Facilities`, `Manager` | — |
| status | TEXT | required | `blocked`, `pending`, `in_progress`, `completed`, `cancelled`, `overdue` | — |
| priority | TEXT | required | `low`, `normal`, `high`, `urgent` | — |
| created_at, due_at | TEXT | required | UTC timestamps; pipeline validates due ordering | — |
| completed_at | TEXT | optional | UTC timestamp >= created_at | — |
| approval_required | INTEGER | required | `0` or `1` | — |
| approved_by | TEXT | optional | Approver identity | — |
| approved_at | TEXT | optional | UTC timestamp >= created_at | — |

### Dependency

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| dependency_id | TEXT | PK, required | `DEP-NNNNNN`; immutable | — |
| task_id | TEXT | FK, required | Dependent task | — |
| prerequisite_task_id | TEXT | FK, required | Required task; must differ from task_id | Tasks form a directed graph; each pair unique |
| created_at | TEXT | required | UTC timestamp | Many-to-many self-relationship between tasks |

### AccessRole

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| access_role_id | TEXT | PK, required | `AROLE-NNN`; immutable | Referenced by many AccessGrant records |
| role_name | TEXT | required, unique | Stable system permission name | — |
| description | TEXT | required | Human-readable purpose | — |
| approval_required | INTEGER | required | `0` or `1` | — |
| created_at | TEXT | required | UTC timestamp | — |

### AccessGrant

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| access_grant_id | TEXT | PK, required | `GRANT-EMP-NNNNNN-NNN`; immutable | — |
| employee_id | TEXT | FK, required | Existing employee | Employee has many historical grants |
| access_role_id | TEXT | FK, required | Existing access role | AccessRole has many grants |
| requested_at | TEXT | required | UTC timestamp | — |
| approved_by, approved_at | TEXT | optional | Approval actor and UTC time; policy rules validated in pipeline | — |
| effective_from | TEXT | required | UTC timestamp; must not precede start/approval in valid baseline | — |
| effective_to | TEXT | optional | UTC timestamp >= effective_from | — |
| status | TEXT | required | `pending`, `active`, `revoked`, `denied`, `expired` | — |
| revoked_at | TEXT | optional | UTC timestamp >= requested_at | — |
| source_task_id | TEXT | FK, optional | Task that initiated grant | Task can initiate many grants |

### Asset

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| asset_id | TEXT | PK, required | `AST-NNNNNN`; immutable | — |
| asset_type | TEXT | required | `laptop`, `phone`, `badge`, `monitor`, `accessory` | — |
| serial_number | TEXT | required, unique | Synthetic inventory serial | — |
| asset_status | TEXT | required | `available`, `assigned`, `in_transit`, `recovered`, `retired`, `lost` | — |
| assigned_employee_id | TEXT | FK, optional | Existing employee | Employee may historically receive assets; active assignment uniqueness checked by validator |
| assigned_at | TEXT | optional | UTC timestamp; present iff assignee is present | — |
| delivered_at | TEXT | optional | UTC timestamp; requires assignment | — |
| acknowledged_at | TEXT | optional | UTC timestamp; requires delivery | — |
| recovered_at | TEXT | optional | UTC timestamp | — |

### AssetAssignment (history bridge)

This additional bridge preserves multiple historical assignments for one asset and makes simultaneous duplicate assignment detectable without duplicate Asset primary keys.

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| asset_assignment_id | TEXT | PK, required | `ASG-NNNNNN`; immutable | — |
| asset_id | TEXT | FK, required | Existing Asset | Asset has many historical assignments |
| employee_id | TEXT | FK, required | Existing Employee | Employee has many historical assignments |
| assignment_status | TEXT | required | `assigned`, `returned`, `cancelled`; at most one active employee per asset | — |
| assigned_at | TEXT | required | UTC timestamp | — |
| delivered_at | TEXT | optional | UTC timestamp >= assignment time | — |
| acknowledged_at | TEXT | optional | UTC timestamp; requires delivery | — |
| recovered_at | TEXT | optional | UTC timestamp >= assignment time | — |

### OffboardingCase

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| offboarding_case_id | TEXT | PK, required | `OFF-YYYY-NNNNNN`; immutable | Parent of offboarding tasks |
| employee_id | TEXT | FK, required | Existing employee; multiple cases allowed to preserve rehire history | Employee has many exit cases over time |
| opened_at | TEXT | required | UTC timestamp | — |
| last_working_date | TEXT | required | ISO date | — |
| exit_type | TEXT | required | `resignation`, `termination`, `contract_end`, `retirement` | — |
| urgency | TEXT | required | `normal`, `urgent` | — |
| status | TEXT | required | `planned`, `in_progress`, `blocked`, `completed`, `cancelled` | — |
| completed_at | TEXT | optional | UTC timestamp >= opened_at | — |

### AuditEvent

| Field | Type | Key / required | Allowed values and validation | Relationships |
|---|---|---|---|---|
| audit_event_id | TEXT | PK, required | `AUD-NNNNNNNNN`; immutable | — |
| entity_type | TEXT | required | `Employee`, `OnboardingCase`, `Task`, `AccessGrant`, `Asset`, `OffboardingCase` | Polymorphic link by entity_type/entity_id; validated by application because SQL cannot enforce a polymorphic FK |
| entity_id | TEXT | required | ID of referenced record | — |
| event_type | TEXT | required | Stable event name, e.g. status transition or approval | — |
| event_at | TEXT | required | UTC timestamp | — |
| actor | TEXT | required | Synthetic user or automation actor | — |
| old_value, new_value | TEXT | optional | JSON scalar/object serialization of changed values | — |
| reason | TEXT | required | Decision or transition explanation | — |

## Lifecycle and history rules

Employee status transitions are intended to be `pending → active → completed/terminated`; application validation will enforce transition chronology. Cases and tasks use the explicit states above. Grants preserve historical rows and change status/effective dates instead of deletion. Asset records retain recovery dates. AuditEvent is append-only by project convention: state changes are represented as events with old/new values and a reason. Role changes are retained through audit events while Employee.role_id represents the current role. Foreign keys protect relational records; AuditEvent's polymorphic reference and graph cycle rules are checked by the validator in later phases.

## Relationship summary

- Department 1:M Employee; Role 1:M Employee; Manager 1:M Employee reports, and a Manager record maps 1:1 to its employee account.
- Employee 1:0..1 OnboardingCase; Employee 1:M OffboardingCase, AccessGrant, and historical Asset assignments.
- Each workflow case 1:M Task. Task M:N Task through Dependency.
- AccessRole 1:M AccessGrant; Task 0..1:M AccessGrant through source_task_id.
- AuditEvent uses a polymorphic entity reference so it can cover several lifecycle entity types without duplicating audit tables.

## Seed data and generated data

`database/seed.sql` provides small stable department, job-role, and access-role vocabularies. It is safe to apply repeatedly after `schema.sql` because inserts use `INSERT OR IGNORE`. Generated people, cases, tasks, assets, grants, and audit events are created by later pipeline phases, not by the seed script.
