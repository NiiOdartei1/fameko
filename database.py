"""
Database initialization and setup
SQLAlchemy database instance
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the app context"""
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created successfully")


def ensure_schema(app):
    """Ensure DB schema has expected columns. Adds missing columns to `orders` table.

    This helper is safe to run multiple times and currently supports SQLite and
    other SQL databases (best-effort). It will add the following columns if
    missing: `cancelled_at`, `cancellation_reason`, `cancellation_notes`.
    """
    with app.app_context():
        engine = db.engine
        conn = engine.connect()
        dialect = engine.dialect.name

        # Ensure orders table exists
        inspector = inspect(engine)
        if 'orders' not in inspector.get_table_names():
            app.logger.info('Orders table missing; creating all tables')
            db.create_all()

        try:
            cols = {c['name'] for c in inspector.get_columns('orders')}
        except Exception:
            # Fallback for SQLite PRAGMA
            try:
                res = conn.execute(text("PRAGMA table_info('orders')")).fetchall()
                cols = {row['name'] if isinstance(row, dict) else row[1] for row in res}
            except Exception:
                cols = set()

        statements = []
        if 'cancelled_at' not in cols:
            if dialect == 'sqlite':
                statements.append("ALTER TABLE orders ADD COLUMN cancelled_at DATETIME")
            else:
                statements.append("ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP")
        if 'cancellation_reason' not in cols:
            statements.append("ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(100)")
        if 'cancellation_notes' not in cols:
            statements.append("ALTER TABLE orders ADD COLUMN cancellation_notes TEXT")

        for stmt in statements:
            try:
                app.logger.info(f'Applying schema change: {stmt}')
                conn.execute(text(stmt))
            except Exception as e:
                app.logger.exception(f'Failed to apply schema change {stmt}: {e}')

        conn.close()
