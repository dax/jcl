-- Exported definition from 2008-11-09T13:58:16
-- Class jcl.model.account.LegacyJID
-- Database: sqlite
CREATE TABLE legacy_j_id (
    id INTEGER PRIMARY KEY,
    legacy_address TEXT,
    jid TEXT,
    account_id INT CONSTRAINT account_id_exists REFERENCES account(id) ,
    child_name VARCHAR (255)
)
