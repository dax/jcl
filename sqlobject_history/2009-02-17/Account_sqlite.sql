-- Exported definition from 2009-02-17T13:58:34
-- Class jcl.model.account.Account
-- Database: sqlite
CREATE TABLE account (
    id INTEGER PRIMARY KEY,
    name TEXT,
    jid TEXT,
    status TEXT,
    error TEXT,
    enabled BOOLEAN,
    lastlogin TIMESTAMP,
    user_table_id INT CONSTRAINT user_table_id_exists REFERENCES user_table(id),
    child_name VARCHAR (255)
);
