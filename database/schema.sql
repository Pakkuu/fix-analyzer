-- schema.sql
-- Full current schema for fix_analyzer database.
-- This file is the single source of truth; keep it in sync with models.py.

CREATE TABLE IF NOT EXISTS orders (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    cl_ord_id       VARCHAR(64)     NOT NULL        COMMENT 'FIX tag 11',
    symbol          VARCHAR(32)     NOT NULL        COMMENT 'FIX tag 55',
    side            VARCHAR(4)      NOT NULL        COMMENT 'FIX tag 54 (1=Buy, 2=Sell)',
    msg_type        VARCHAR(16)     NOT NULL        COMMENT 'Human-readable msg type',
    order_qty       DECIMAL(18,6)   DEFAULT NULL    COMMENT 'FIX tag 38',
    price           DECIMAL(18,6)   DEFAULT NULL    COMMENT 'FIX tag 44',
    fill_price      DECIMAL(18,6)   DEFAULT NULL    COMMENT 'Execution fill price',
    status          VARCHAR(32)     DEFAULT NULL    COMMENT 'FIX tag 39 OrdStatus',
    seq_num         INT             DEFAULT NULL    COMMENT 'FIX tag 34',
    sender_comp_id  VARCHAR(64)     DEFAULT NULL    COMMENT 'FIX tag 49',
    target_comp_id  VARCHAR(64)     DEFAULT NULL    COMMENT 'FIX tag 56',
    raw_fix         TEXT            NOT NULL        COMMENT 'Original FIX message verbatim',
    received_at     DATETIME        NOT NULL        COMMENT 'Timestamp when record was persisted',

    PRIMARY KEY (id),
    INDEX ix_orders_symbol          (symbol),
    INDEX ix_orders_cl_ord_id       (cl_ord_id),
    INDEX ix_orders_msg_type        (msg_type),
    INDEX ix_orders_received_at     (received_at),
    INDEX ix_orders_symbol_received (symbol, received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS anomalies (
    id              BIGINT          NOT NULL AUTO_INCREMENT,
    order_id        BIGINT          NOT NULL,
    anomaly_type    VARCHAR(64)     NOT NULL        COMMENT 'e.g. DUPLICATE, PRICE_SPIKE',
    severity        VARCHAR(16)     DEFAULT 'MEDIUM',
    description     TEXT            DEFAULT NULL,
    raw_fix         TEXT            DEFAULT NULL    COMMENT 'Relevant FIX snippet',
    detected_at     DATETIME        NOT NULL        COMMENT 'Timestamp when anomaly was detected',

    PRIMARY KEY (id),
    INDEX ix_anomalies_order_id     (order_id),
    INDEX ix_anomalies_type         (anomaly_type),
    INDEX ix_anomalies_detected_at  (detected_at),

    CONSTRAINT fk_anomalies_order
        FOREIGN KEY (order_id) REFERENCES orders (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
