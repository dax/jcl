alter table user rename to user_table;
begin transaction;
CREATE TEMPORARY TABLE account_backup (
    id INTEGER PRIMARY KEY,
    name TEXT,
    jid TEXT,
    status TEXT,
    error TEXT,
    enabled BOOLEAN,
    lastlogin TIMESTAMP,
    user_id INT CONSTRAINT user_id_exists REFERENCES user_table(id) ,
    child_name VARCHAR (255)
);
INSERT INTO account_backup SELECT * FROM account;
DROP TABLE account;
CREATE TABLE account (
    id INTEGER PRIMARY KEY,
    name TEXT,
    jid TEXT,
    status TEXT,
    error TEXT,
    enabled BOOLEAN,
    lastlogin TIMESTAMP,
    user_id INT CONSTRAINT user_id_exists REFERENCES user_table(id) ,
    child_name VARCHAR (255)
);
INSERT INTO account SELECT * FROM account;
DROP TABLE account_backup;
commit;

