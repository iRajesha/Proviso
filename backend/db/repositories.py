import json
from backend.db.connection import get_connection
from backend.db.models import GoldScript, GenerationLog, SearchResult


class GoldScriptRepository:
    def save(
        self,
        title: str,
        use_case: str,
        services: list[str],
        terraform_code: str,
        cleanup_script: str,
        change_summary: str,
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()
        var_id = cur.var(int)
        cur.execute(
            """
            INSERT INTO gold_scripts
                (title, use_case, services, terraform_code, cleanup_script, change_summary)
            VALUES (:1, :2, :3, :4, :5, :6)
            RETURNING id INTO :7
            """,
            (
                title,
                use_case,
                ",".join(services),
                terraform_code,
                cleanup_script,
                change_summary,
                var_id,
            ),
        )
        conn.commit()
        cur.close()
        return var_id.getvalue()[0]

    def hybrid_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """
        ADB 26ai hybrid search: vector similarity + Oracle Text full-text,
        combined with RRF (Reciprocal Rank Fusion).
        """
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, use_case, services, combined_score
            FROM (
                SELECT
                    id, title, use_case, services,
                    (0.7 * vec_score + 0.3 * ft_score) AS combined_score
                FROM (
                    SELECT
                        id, title, use_case, services,
                        VECTOR_DISTANCE(
                            embedding,
                            TO_VECTOR(DBMS_VECTOR.UTL_TO_EMBEDDING(
                                :query,
                                JSON(''{"provider":"database","model":"ALL_MINILM_L12_V2"}'')
                            )),
                            COSINE
                        ) AS vec_score,
                        SCORE(1) AS ft_score
                    FROM gold_scripts
                    WHERE CONTAINS(use_case, :query, 1) > 0
                       OR VECTOR_DISTANCE(
                            embedding,
                            TO_VECTOR(DBMS_VECTOR.UTL_TO_EMBEDDING(
                                :query,
                                JSON(''{"provider":"database","model":"ALL_MINILM_L12_V2"}'')
                            )),
                            COSINE
                          ) < 0.5
                )
            )
            ORDER BY combined_score DESC
            FETCH FIRST :limit ROWS ONLY
            """,
            {"query": query, "limit": limit},
        )
        rows = cur.fetchall()
        cur.close()
        return [
            SearchResult(
                id=r[0],
                title=r[1],
                use_case=r[2],
                services=r[3].split(",") if r[3] else [],
                score=float(r[4] or 0),
                snippet=r[2][:200],
            )
            for r in rows
        ]

    def get_by_id(self, script_id: int) -> GoldScript | None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, use_case, services,
                   terraform_code, cleanup_script, change_summary,
                   created_at, updated_at
            FROM gold_scripts WHERE id = :1
            """,
            (script_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return GoldScript(
            id=row[0],
            title=row[1],
            use_case=row[2],
            services=row[3].split(",") if row[3] else [],
            terraform_code=row[4].read() if hasattr(row[4], "read") else str(row[4]),
            cleanup_script=row[5].read() if hasattr(row[5], "read") else str(row[5] or ""),
            change_summary=row[6].read() if hasattr(row[6], "read") else str(row[6] or ""),
            created_at=row[7],
            updated_at=row[8],
        )


class GenerationLogRepository:
    def log(
        self,
        session_id: str,
        requirements: str,
        services: list[str],
        generated_terraform: str,
        reviewed_terraform: str,
        change_summary: str,
        cleanup_script: str,
    ) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO generation_log
                (session_id, requirements, services,
                 generated_terraform, reviewed_terraform,
                 change_summary, cleanup_script)
            VALUES (:1, :2, :3, :4, :5, :6, :7)
            """,
            (
                session_id,
                requirements,
                ",".join(services),
                generated_terraform,
                reviewed_terraform,
                change_summary,
                cleanup_script,
            ),
        )
        conn.commit()
        cur.close()
