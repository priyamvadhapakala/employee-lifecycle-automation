PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Department (
    department_id TEXT PRIMARY KEY CHECK (department_id GLOB 'DEPT-[0-9][0-9][0-9]'),
    department_name TEXT NOT NULL UNIQUE,
    cost_center TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Role (
    role_id TEXT PRIMARY KEY CHECK (role_id GLOB 'ROLE-[0-9][0-9][0-9]'),
    role_name TEXT NOT NULL UNIQUE,
    role_family TEXT NOT NULL,
    employment_type_default TEXT NOT NULL CHECK (employment_type_default IN ('full_time','contractor')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Manager (
    manager_id TEXT PRIMARY KEY CHECK (manager_id GLOB 'MGR-[0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL UNIQUE,
    active_from TEXT NOT NULL,
    active_to TEXT,
    CHECK (active_to IS NULL OR active_to >= active_from),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS Employee (
    employee_id TEXT PRIMARY KEY CHECK (employee_id GLOB 'EMP-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    manager_id TEXT,
    employment_type TEXT NOT NULL CHECK (employment_type IN ('full_time','contractor')),
    employment_status TEXT NOT NULL CHECK (employment_status IN ('pending','active','completed','terminated')),
    hire_date TEXT NOT NULL,
    planned_start_date TEXT NOT NULL,
    actual_start_date TEXT,
    termination_date TEXT,
    location TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (actual_start_date IS NULL OR actual_start_date >= hire_date),
    CHECK (termination_date IS NULL OR termination_date >= hire_date),
    FOREIGN KEY (department_id) REFERENCES Department(department_id),
    FOREIGN KEY (role_id) REFERENCES Role(role_id),
    FOREIGN KEY (manager_id) REFERENCES Manager(manager_id)
);

CREATE TABLE IF NOT EXISTS OnboardingCase (
    onboarding_case_id TEXT PRIMARY KEY CHECK (onboarding_case_id GLOB 'ONB-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL UNIQUE,
    opened_at TEXT NOT NULL,
    planned_start_date TEXT NOT NULL,
    actual_start_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('planned','in_progress','blocked','completed','cancelled')),
    completed_at TEXT,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    CHECK (completed_at IS NULL OR completed_at >= opened_at),
    CHECK (actual_start_date IS NULL OR actual_start_date >= opened_at)
);

CREATE TABLE IF NOT EXISTS Task (
    task_id TEXT PRIMARY KEY CHECK (
        task_id GLOB 'TASK-ONB-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]' OR
        task_id GLOB 'TASK-OFF-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'
    ),
    onboarding_case_id TEXT,
    offboarding_case_id TEXT,
    task_type TEXT NOT NULL,
    owner_team TEXT NOT NULL CHECK (owner_team IN ('HR','IT','Facilities','Manager')),
    status TEXT NOT NULL CHECK (status IN ('blocked','pending','in_progress','completed','cancelled','overdue')),
    priority TEXT NOT NULL CHECK (priority IN ('low','normal','high','urgent')),
    created_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    completed_at TEXT,
    approval_required INTEGER NOT NULL DEFAULT 0 CHECK (approval_required IN (0,1)),
    approved_by TEXT,
    approved_at TEXT,
    CHECK ((onboarding_case_id IS NOT NULL) + (offboarding_case_id IS NOT NULL) = 1),
    CHECK (completed_at IS NULL OR completed_at >= created_at),
    CHECK (approved_at IS NULL OR approved_at >= created_at),
    FOREIGN KEY (onboarding_case_id) REFERENCES OnboardingCase(onboarding_case_id),
    FOREIGN KEY (offboarding_case_id) REFERENCES OffboardingCase(offboarding_case_id)
);

CREATE TABLE IF NOT EXISTS Dependency (
    dependency_id TEXT PRIMARY KEY CHECK (dependency_id GLOB 'DEP-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    task_id TEXT NOT NULL,
    prerequisite_task_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (task_id, prerequisite_task_id),
    CHECK (task_id <> prerequisite_task_id),
    FOREIGN KEY (task_id) REFERENCES Task(task_id),
    FOREIGN KEY (prerequisite_task_id) REFERENCES Task(task_id)
);

CREATE TABLE IF NOT EXISTS AccessRole (
    access_role_id TEXT PRIMARY KEY CHECK (access_role_id GLOB 'AROLE-[0-9][0-9][0-9]'),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    approval_required INTEGER NOT NULL CHECK (approval_required IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS AccessGrant (
    access_grant_id TEXT PRIMARY KEY CHECK (access_grant_id GLOB 'GRANT-EMP-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL,
    access_role_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending','active','revoked','denied','expired')),
    revoked_at TEXT,
    source_task_id TEXT,
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CHECK (revoked_at IS NULL OR revoked_at >= requested_at),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    FOREIGN KEY (access_role_id) REFERENCES AccessRole(access_role_id),
    FOREIGN KEY (source_task_id) REFERENCES Task(task_id)
);

CREATE TABLE IF NOT EXISTS Asset (
    asset_id TEXT PRIMARY KEY CHECK (asset_id GLOB 'AST-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    asset_type TEXT NOT NULL CHECK (asset_type IN ('laptop','phone','badge','monitor','accessory')),
    serial_number TEXT NOT NULL UNIQUE,
    asset_status TEXT NOT NULL CHECK (asset_status IN ('available','assigned','in_transit','recovered','retired','lost')),
    assigned_employee_id TEXT,
    assigned_at TEXT,
    delivered_at TEXT,
    acknowledged_at TEXT,
    recovered_at TEXT,
    CHECK ((assigned_employee_id IS NULL) = (assigned_at IS NULL)),
    CHECK (delivered_at IS NULL OR assigned_at IS NOT NULL),
    CHECK (acknowledged_at IS NULL OR delivered_at IS NOT NULL),
    FOREIGN KEY (assigned_employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS AssetAssignment (
    asset_assignment_id TEXT PRIMARY KEY CHECK (asset_assignment_id GLOB 'ASG-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    asset_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    assignment_status TEXT NOT NULL CHECK (assignment_status IN ('assigned','returned','cancelled')),
    assigned_at TEXT NOT NULL,
    delivered_at TEXT,
    acknowledged_at TEXT,
    recovered_at TEXT,
    FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    CHECK (delivered_at IS NULL OR delivered_at >= assigned_at),
    CHECK (acknowledged_at IS NULL OR delivered_at IS NOT NULL),
    CHECK (recovered_at IS NULL OR recovered_at >= assigned_at)
);

CREATE TABLE IF NOT EXISTS OffboardingCase (
    offboarding_case_id TEXT PRIMARY KEY CHECK (offboarding_case_id GLOB 'OFF-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    last_working_date TEXT NOT NULL,
    exit_type TEXT NOT NULL CHECK (exit_type IN ('resignation','termination','contract_end','retirement')),
    urgency TEXT NOT NULL CHECK (urgency IN ('normal','urgent')),
    status TEXT NOT NULL CHECK (status IN ('planned','in_progress','blocked','completed','cancelled')),
    completed_at TEXT,
    CHECK (completed_at IS NULL OR completed_at >= opened_at),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS AuditEvent (
    audit_event_id TEXT PRIMARY KEY CHECK (audit_event_id GLOB 'AUD-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('Employee','OnboardingCase','Task','AccessGrant','Asset','OffboardingCase')),
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_employee_department ON Employee(department_id);
CREATE INDEX IF NOT EXISTS idx_employee_status ON Employee(employment_status);
CREATE INDEX IF NOT EXISTS idx_task_onboarding ON Task(onboarding_case_id);
CREATE INDEX IF NOT EXISTS idx_task_offboarding ON Task(offboarding_case_id);
CREATE INDEX IF NOT EXISTS idx_task_status_due ON Task(status, due_at);
CREATE INDEX IF NOT EXISTS idx_dependency_prerequisite ON Dependency(prerequisite_task_id);
CREATE INDEX IF NOT EXISTS idx_grant_employee_status ON AccessGrant(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_asset_assignee ON Asset(assigned_employee_id);
CREATE INDEX IF NOT EXISTS idx_asset_assignment_asset_status ON AssetAssignment(asset_id, assignment_status);
CREATE INDEX IF NOT EXISTS idx_asset_assignment_employee ON AssetAssignment(employee_id);
CREATE INDEX IF NOT EXISTS idx_offboarding_employee ON OffboardingCase(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON AuditEvent(entity_type, entity_id, event_at);
