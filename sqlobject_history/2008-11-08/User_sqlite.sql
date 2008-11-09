-- Exported definition from 2008-11-09T13:58:16
-- Class jcl.model.account.User
-- Database: sqlite
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    jid TEXT,
    has_received_motd BOOLEAN,
    child_name VARCHAR (255)
)
