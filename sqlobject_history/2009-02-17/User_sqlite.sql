-- Exported definition from 2009-02-17T13:58:34
-- Class jcl.model.account.User
-- Database: sqlite
CREATE TABLE user_table (
    id INTEGER PRIMARY KEY,
    jid TEXT,
    has_received_motd BOOLEAN,
    child_name VARCHAR (255)
);
