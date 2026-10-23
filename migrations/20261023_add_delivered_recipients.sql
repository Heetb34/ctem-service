-- Run once on existing MySQL databases before deploying this scheduler version.
-- Fresh databases receive this nullable column from SQLAlchemy create_all.
ALTER TABLE report_schedules
  ADD COLUMN delivered_recipients JSON NULL;
