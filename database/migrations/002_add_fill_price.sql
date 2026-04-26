-- migrations/002_add_fill_price.sql
-- Add fill_price column for execution reports.

ALTER TABLE orders
    ADD COLUMN fill_price DECIMAL(18,6) DEFAULT NULL
    COMMENT 'Execution fill price'
    AFTER price;
