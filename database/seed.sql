-- Minimal stable organizational vocabulary. Timestamps are fixed for reproducibility.
INSERT OR IGNORE INTO Department (department_id, department_name, cost_center, created_at) VALUES
('DEPT-001', 'People Operations', 'CC-100', '2026-01-01T00:00:00Z'),
('DEPT-002', 'Engineering', 'CC-200', '2026-01-01T00:00:00Z'),
('DEPT-003', 'Finance', 'CC-300', '2026-01-01T00:00:00Z'),
('DEPT-004', 'Customer Operations', 'CC-400', '2026-01-01T00:00:00Z');

INSERT OR IGNORE INTO Role (role_id, role_name, role_family, employment_type_default, created_at) VALUES
('ROLE-001', 'People Partner', 'People', 'full_time', '2026-01-01T00:00:00Z'),
('ROLE-002', 'Software Engineer', 'Engineering', 'full_time', '2026-01-01T00:00:00Z'),
('ROLE-003', 'Financial Analyst', 'Finance', 'full_time', '2026-01-01T00:00:00Z'),
('ROLE-004', 'Support Specialist', 'Customer Operations', 'contractor', '2026-01-01T00:00:00Z');

INSERT OR IGNORE INTO AccessRole (access_role_id, role_name, description, approval_required, created_at) VALUES
('AROLE-001', 'email_standard', 'Standard company email and calendar', 0, '2026-01-01T00:00:00Z'),
('AROLE-002', 'source_control', 'Source code repository access', 1, '2026-01-01T00:00:00Z'),
('AROLE-003', 'finance_system', 'Finance system access', 1, '2026-01-01T00:00:00Z'),
('AROLE-004', 'support_console', 'Customer support console access', 1, '2026-01-01T00:00:00Z');
