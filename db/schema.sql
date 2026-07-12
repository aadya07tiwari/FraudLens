-- FraudLens: PaySim transactions schema
-- This is the schema the NL-to-SQL agent is told about (schema-aware prompting).

CREATE TABLE IF NOT EXISTS transactions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    step              INTEGER,      -- time unit (1 step = 1 hour, PaySim convention)
    type              TEXT,         -- CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER
    amount            REAL,
    nameOrig          TEXT,         -- origin account id
    oldbalanceOrg     REAL,
    newbalanceOrig    REAL,
    nameDest          TEXT,         -- destination account id
    oldbalanceDest    REAL,
    newbalanceDest    REAL,
    isFraud           INTEGER,      -- 1 if the transaction is a known fraud
    isFlaggedFraud    INTEGER       -- 1 if PaySim's own rule flagged it
);

CREATE INDEX IF NOT EXISTS idx_txn_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_txn_nameOrig ON transactions(nameOrig);
CREATE INDEX IF NOT EXISTS idx_txn_nameDest ON transactions(nameDest);
CREATE INDEX IF NOT EXISTS idx_txn_isFraud ON transactions(isFraud);
CREATE INDEX IF NOT EXISTS idx_txn_step ON transactions(step);
