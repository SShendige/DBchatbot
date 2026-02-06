import logging
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List

# Configure logging for observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_access")

class DatabaseService:
    """
    This service owns all SQL. The LLM never sees this.
    All data is validated and filtered here.
    """

    def __init__(self):
        # We want to fail fast if DB params are wrong, rather than falling back silently.
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "dsedifylms"),
                user=os.getenv("DB_USER", "lms_api_user"),
                password=os.getenv("DB_PASSWORD")
            )
            logger.info("Connected to database successfully.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to connect to DB: {e}")
            logger.error(f"Params: host={os.getenv('DB_HOST')}, dbname={os.getenv('DB_NAME')}, user={os.getenv('DB_USER')}")
            # We will still set to None to allow app startup, but we'll return explicit error on task exec
            self.conn = None

    async def execute_task(self, task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        if not self.conn:
             # Explicitly fail if no DB connection
             raise Exception("Database connection is unavailable. Check server logs for credentials errors.")

        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            if task_id == "get_student_assessment_score":
                result = self._get_student_assessment_score(cursor, params)
            elif task_id == "list_assessments_by_level":
                result = self._list_assessments_by_level(cursor, params)
            elif task_id == "get_question_distribution":
                result = self._get_question_distribution(cursor, params)
            elif task_id == "get_assessment_summary":
                 result = self._get_assessment_summary(cursor, params)
            else:
                raise ValueError(f"Task {task_id} not implemented in backend")

            execution_time = time.time() - start_time
            
            # Observability: Log metadata, not raw data
            row_count = len(result.get('data', [])) if 'data' in result else 0
            logger.info(f"TASK_EXEC: id={task_id} status=success rows={row_count} duration={execution_time:.3f}s")
            
            return result
        except Exception as e:
            logger.error(f"TASK_EXEC: id={task_id} status=error message={str(e)}")
            self.conn.rollback() # Ensure transaction is cleared on error
            raise

    def _get_student_assessment_score(self, cursor, params: Dict[str, Any]) -> Dict[str, Any]:
        # Based on inspection: assessment.student_assessments
        
        cursor.execute("""
            SELECT student_id, total_score, updated_at 
            FROM assessment.student_assessments 
            WHERE student_id = %s 
            LIMIT 10
        """, (params['student_id'],))
        data = cursor.fetchall()
        return {"data": data}

    def _list_assessments_by_level(self, cursor, params: Dict[str, Any]) -> Dict[str, Any]:
        level = params.get('level')
        
        # Based on inspection: assessment.assessments
        sql = "SELECT assessment_name, assessment_level, duration_in_mins FROM assessment.assessments WHERE 1=1"
        args = []
        
        if level:
            sql += " AND assessment_level = %s"
            args.append(level)

        cursor.execute(sql + " LIMIT 20", tuple(args))
        return {"data": cursor.fetchall()}

    def _get_question_distribution(self, cursor, params: Dict[str, Any]) -> Dict[str, Any]:
        # Based on inspection: assessment.assessment_questions
        cursor.execute("""
            SELECT question_type, COUNT(*) as count, AVG(weightage) as avg_weight 
            FROM assessment.assessment_questions 
            WHERE level3_category_id = %s 
            GROUP BY question_type
        """, (params['category_id'],))
        return {"data": cursor.fetchall()}

    def _get_assessment_summary(self, cursor, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get('assessment_name', '')
        # Based on inspection: assessment.assessments
        cursor.execute("""
            SELECT assessment_name, duration_in_mins, quest_per_assess 
            FROM assessment.assessments 
            WHERE assessment_name ILIKE %s
        """, (f"%{name}%",))
        return {"data": cursor.fetchall()}

    def _get_mock_data(self, task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Fallback if DB not reachable
        if task_id == "get_student_assessment_score":
             return {"data": [{"student_id": params.get('student_id'), "total_score": 85, "created_at": "2024-03-15"}]}
        return {"data": [], "message": "DB Connection Failed - Returning Mock"}
