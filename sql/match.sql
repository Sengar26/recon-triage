-- Phase 4: deterministic bank-to-GL matching in DuckDB.
-- Run through src/match.py, from the project folder (file paths are relative to it).
--
-- Every bank row and every GL row may be used at most once. Each pass only
-- looks at rows that earlier passes left unmatched. Within a pass, a pair is
-- kept only if each side is the other's best (closest-date) candidate.

-- ---------------------------------------------------------------- load
CREATE OR REPLACE TABLE bank AS
SELECT bank_id,
       CAST(value_date AS DATE)          AS value_date,
       CAST(amount_inr AS DECIMAL(14,2)) AS amount_inr,
       description,
       NULLIF(TRIM(reference), '')       AS reference
FROM read_csv('data/bank.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE gl AS
SELECT gl_id,
       CAST(posting_date AS DATE)        AS posting_date,
       CAST(amount_inr AS DECIMAL(14,2)) AS amount_inr,
       currency,
       counterparty,
       NULLIF(TRIM(reference), '')       AS reference
FROM read_csv('data/gl.csv', header = true, all_varchar = true);

-- ---------------------------------------------------------------- pass 1
-- Same reference, same amount, bank date 0-5 days after the GL date.
CREATE OR REPLACE TABLE pass1 AS
WITH candidates AS (
    SELECT b.bank_id, g.gl_id,
           date_diff('day', g.posting_date, b.value_date) AS date_gap
    FROM bank b
    JOIN gl g
      ON b.reference = g.reference
     AND b.amount_inr = g.amount_inr
     AND date_diff('day', g.posting_date, b.value_date) BETWEEN 0 AND 5
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY bank_id ORDER BY date_gap, gl_id)   AS bank_rank,
           ROW_NUMBER() OVER (PARTITION BY gl_id   ORDER BY date_gap, bank_id) AS gl_rank
    FROM candidates
)
SELECT bank_id, gl_id, 1 AS pass
FROM ranked
WHERE bank_rank = 1 AND gl_rank = 1;

-- ---------------------------------------------------------------- pass 2
-- Bank row has no reference: same amount, dates within 5 days, closest date wins.
CREATE OR REPLACE TABLE pass2 AS
WITH open_bank AS (
    SELECT * FROM bank
    WHERE reference IS NULL
      AND bank_id NOT IN (SELECT bank_id FROM pass1)
),
open_gl AS (
    SELECT * FROM gl
    WHERE gl_id NOT IN (SELECT gl_id FROM pass1)
),
candidates AS (
    SELECT b.bank_id, g.gl_id,
           abs(date_diff('day', g.posting_date, b.value_date)) AS date_gap
    FROM open_bank b
    JOIN open_gl g
      ON b.amount_inr = g.amount_inr
     AND abs(date_diff('day', g.posting_date, b.value_date)) <= 5
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY bank_id ORDER BY date_gap, gl_id)   AS bank_rank,
           ROW_NUMBER() OVER (PARTITION BY gl_id   ORDER BY date_gap, bank_id) AS gl_rank
    FROM candidates
)
SELECT bank_id, gl_id, 2 AS pass
FROM ranked
WHERE bank_rank = 1 AND gl_rank = 1;

CREATE OR REPLACE TABLE matched AS
SELECT * FROM pass1
UNION ALL
SELECT * FROM pass2;

-- ---------------------------------------------------------------- pass 3
-- Same reference, different amount: not cleared, but paired as one exception.
CREATE OR REPLACE TABLE pass3 AS
WITH open_bank AS (
    SELECT * FROM bank WHERE bank_id NOT IN (SELECT bank_id FROM matched)
),
open_gl AS (
    SELECT * FROM gl WHERE gl_id NOT IN (SELECT gl_id FROM matched)
),
candidates AS (
    SELECT b.bank_id, g.gl_id,
           abs(date_diff('day', g.posting_date, b.value_date)) AS date_gap
    FROM open_bank b
    JOIN open_gl g
      ON b.reference = g.reference
     AND b.amount_inr <> g.amount_inr
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY bank_id ORDER BY date_gap, gl_id)   AS bank_rank,
           ROW_NUMBER() OVER (PARTITION BY gl_id   ORDER BY date_gap, bank_id) AS gl_rank
    FROM candidates
)
SELECT bank_id, gl_id
FROM ranked
WHERE bank_rank = 1 AND gl_rank = 1;

-- ---------------------------------------------------------------- exceptions
-- Everything not cleared: amount-mismatch pairs, then leftover rows on either side.
CREATE OR REPLACE TABLE exceptions AS
WITH items AS (
    SELECT 'amount_mismatch' AS kind, p.bank_id, p.gl_id,
           least(b.value_date, g.posting_date) AS item_date
    FROM pass3 p
    JOIN bank b USING (bank_id)
    JOIN gl g USING (gl_id)

    UNION ALL
    SELECT 'bank_only', bank_id, NULL, value_date
    FROM bank
    WHERE bank_id NOT IN (SELECT bank_id FROM matched)
      AND bank_id NOT IN (SELECT bank_id FROM pass3)

    UNION ALL
    SELECT 'gl_only', NULL, gl_id, posting_date
    FROM gl
    WHERE gl_id NOT IN (SELECT gl_id FROM matched)
      AND gl_id NOT IN (SELECT gl_id FROM pass3)
)
SELECT printf('EXC-%04d',
              ROW_NUMBER() OVER (ORDER BY item_date, coalesce(bank_id, gl_id), gl_id)) AS exception_id,
       kind, bank_id, gl_id
FROM items;
