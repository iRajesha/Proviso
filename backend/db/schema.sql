-- =============================================================
-- Proviso ADB 26ai Schema
-- Run as ADMIN or DBA user, grants to WORKBENCH_USER
-- =============================================================

-- Load ONNX embedding model into DB (run once)
-- EXEC DBMS_VECTOR.LOAD_ONNX_MODEL(
--     'OBJ_STORE_DIR',
--     'all-minilm-l12-v2.onnx',
--     'ALL_MINILM_L12_V2',
--     JSON('{"function":"embedding","embeddingOutput":"embedding"}')
-- );

CREATE TABLE IF NOT EXISTS gold_scripts (
    id               NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title            VARCHAR2(500)  NOT NULL,
    use_case         VARCHAR2(2000) NOT NULL,
    services         VARCHAR2(1000),                    -- comma-separated
    terraform_code   CLOB           NOT NULL,
    cleanup_script   CLOB,
    change_summary   CLOB,
    embedding        VECTOR(384, FLOAT32),              -- ADB 26ai VECTOR type
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW vector index for fast approximate nearest-neighbor search
CREATE VECTOR INDEX IF NOT EXISTS gold_scripts_hnsw_idx
    ON gold_scripts (embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;

-- Full-text index for hybrid search
CREATE INDEX IF NOT EXISTS gold_scripts_ft_idx
    ON gold_scripts (use_case) INDEXTYPE IS CTXSYS.CONTEXT;

-- Trigger: auto-embed on insert / update
CREATE OR REPLACE TRIGGER gold_scripts_embed_trg
BEFORE INSERT OR UPDATE OF use_case, terraform_code ON gold_scripts
FOR EACH ROW
BEGIN
    :NEW.embedding := TO_VECTOR(
        DBMS_VECTOR.UTL_TO_EMBEDDING(
            :NEW.use_case || ' ' || SUBSTR(:NEW.terraform_code, 1, 2000),
            JSON('{"provider":"database","model":"ALL_MINILM_L12_V2"}')
        )
    );
    :NEW.updated_at := CURRENT_TIMESTAMP;
END;
/

-- Generation audit log
CREATE TABLE IF NOT EXISTS generation_log (
    id                  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id          VARCHAR2(100),
    requirements        CLOB           NOT NULL,
    services            VARCHAR2(1000),
    generated_terraform CLOB,
    reviewed_terraform  CLOB,
    change_summary      CLOB,
    cleanup_script      CLOB,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- JSON-Relational Duality View for ORDS REST exposure
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW gold_scripts_jdv AS
SELECT JSON {
    'id'           : g.id,
    'title'        : g.title,
    'use_case'     : g.use_case,
    'services'     : g.services,
    'change_summary': g.change_summary,
    'created_at'   : g.created_at
}
FROM gold_scripts g WITH NOINSERT NOUPDATE NODELETE;

GRANT SELECT, INSERT, UPDATE ON gold_scripts  TO WORKBENCH_USER;
GRANT SELECT, INSERT         ON generation_log TO WORKBENCH_USER;
GRANT SELECT                 ON gold_scripts_jdv TO WORKBENCH_USER;
