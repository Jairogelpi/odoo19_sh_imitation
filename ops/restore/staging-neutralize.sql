\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
  v_mail_server_id integer;
  v_staging_url text := NULLIF(:'staging_web_base_url', '');
  v_mailpit_host text := COALESCE(NULLIF(:'staging_mailpit_host', ''), 'mailpit');
  v_mailpit_port integer := COALESCE(NULLIF(:'staging_mailpit_port', '')::integer, 1025);
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'ir_mail_server'
  ) THEN
    UPDATE ir_mail_server
    SET
      active = FALSE,
      smtp_user = NULL,
      smtp_pass = NULL,
      smtp_encryption = 'none',
      smtp_authentication = NULL,
      smtp_debug = FALSE,
      from_filter = NULL;

    SELECT id
    INTO v_mail_server_id
    FROM ir_mail_server
    ORDER BY COALESCE(sequence, 999999), id
    LIMIT 1;

    IF v_mail_server_id IS NOT NULL THEN
      UPDATE ir_mail_server
      SET
        name = 'Staging Mailpit',
        active = TRUE,
        smtp_host = v_mailpit_host,
        smtp_port = v_mailpit_port,
        smtp_user = NULL,
        smtp_pass = NULL,
        smtp_encryption = 'none',
        smtp_authentication = NULL,
        smtp_debug = FALSE,
        from_filter = NULL
      WHERE id = v_mail_server_id;
    END IF;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'fetchmail_server'
  ) THEN
    UPDATE fetchmail_server
    SET active = FALSE;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'ir_cron'
  ) THEN
    UPDATE ir_cron
    SET active = FALSE;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'mail_mail'
  ) THEN
    UPDATE mail_mail
    SET
      state = 'cancel',
      failure_reason = CASE
        WHEN COALESCE(failure_reason, '') = '' THEN 'Cancelled by staging neutralization.'
        ELSE failure_reason || E'\nCancelled by staging neutralization.'
      END
    WHERE state = 'outgoing';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'sms_sms'
  ) THEN
    UPDATE sms_sms
    SET
      state = 'error',
      failure_type = 'staging_neutralized'
    WHERE state IN ('outgoing', 'process', 'pending');
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'ir_config_parameter'
  ) THEN
    INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
    VALUES ('platform.staging_neutralized', 'true', NULL, NULL, NOW(), NOW())
    ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value, write_uid = NULL, write_date = NOW();

    IF v_staging_url IS NOT NULL THEN
      INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
      VALUES ('web.base.url', v_staging_url, NULL, NULL, NOW(), NOW())
      ON CONFLICT (key) DO UPDATE
      SET value = EXCLUDED.value, write_uid = NULL, write_date = NOW();
    END IF;
  END IF;
END $$;

COMMIT;
