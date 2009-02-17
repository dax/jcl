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
    user_table_id INT CONSTRAINT user_table_id_exists REFERENCES user_table(id),
    child_name VARCHAR (255)
);
INSERT INTO account SELECT * FROM account_backup;
DROP TABLE account_backup;
commit;

