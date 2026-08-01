BEGIN;

CREATE TABLE IF NOT EXISTS dnc_events (
    tenant_id text NOT NULL,
    aggregate_id text NOT NULL,
    aggregate_version bigint NOT NULL,
    event_id text NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, aggregate_id, aggregate_version),
    UNIQUE (tenant_id, event_id)
);

CREATE TABLE IF NOT EXISTS dnc_outbox (
    tenant_id text NOT NULL,
    message_id text NOT NULL,
    idempotency_key text NOT NULL,
    topic text NOT NULL,
    payload jsonb NOT NULL,
    published_at timestamptz,
    PRIMARY KEY (tenant_id, message_id),
    UNIQUE (tenant_id, idempotency_key)
);

ALTER TABLE dnc_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE dnc_events FORCE ROW LEVEL SECURITY;
ALTER TABLE dnc_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE dnc_outbox FORCE ROW LEVEL SECURITY;

CREATE POLICY dnc_events_tenant ON dnc_events
    USING (tenant_id = current_setting('dnc.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('dnc.tenant_id', true));
CREATE POLICY dnc_outbox_tenant ON dnc_outbox
    USING (tenant_id = current_setting('dnc.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('dnc.tenant_id', true));

COMMIT;
