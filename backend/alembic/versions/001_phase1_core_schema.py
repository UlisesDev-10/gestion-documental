"""001_phase1_core_schema

Revision ID: 001_phase1_core
Revises: None
Create Date: 2026-11-22 14:15:00.000000

Esquema inicial de la Fase 1 (Núcleo):
- Extensiones: uuid-ossp, pg_trgm
- ENUMs: rol_usuario_enum, nivel_acceso_enum, estado_revision_enum
- Tablas: usuarios, carpetas, archivos, versiones, permisos, bitacora
- Triggers de inmutabilidad en versiones y bitacora
- Indices optimizados para exploracion, busqueda textual y deduplicacion
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_phase1_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensiones de PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    # 2. Tipos Enumerados (ENUMs)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rol_usuario_enum AS ENUM ('administrador', 'editor', 'revisor', 'lector');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE nivel_acceso_enum AS ENUM ('lectura', 'edicion', 'administracion');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE estado_revision_enum AS ENUM ('sin_revision', 'pendiente', 'revisado', 'con_observaciones');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # 3. Tabla usuarios
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nombre_completo", sa.String(255), nullable=False),
        sa.Column("rol", postgresql.ENUM("administrador", "editor", "revisor", "lector", name="rol_usuario_enum", create_type=False), nullable=False, server_default="lector"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # 4. Tabla carpetas
    op.create_table(
        "carpetas",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("carpeta_padre_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("en_papelera", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["carpeta_padre_id"], ["carpetas.id"], name="fk_carpetas_padre", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"], name="fk_carpetas_creador", ondelete="RESTRICT"),
    )

    # 5. Tabla archivos
    op.create_table(
        "archivos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("carpeta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("version_vigente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bloqueado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bloqueado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bloqueo_expira_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado_revision", postgresql.ENUM("sin_revision", "pendiente", "revisado", "con_observaciones", name="estado_revision_enum", create_type=False), nullable=False, server_default="sin_revision"),
        sa.Column("en_papelera", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["carpeta_id"], ["carpetas.id"], name="fk_archivos_carpeta", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bloqueado_por"], ["usuarios.id"], name="fk_archivos_bloqueado_por", ondelete="SET NULL"),
    )

    # 6. Tabla versiones
    op.create_table(
        "versiones",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("archivo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False),
        sa.Column("autor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=False),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.CHAR(64), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["archivo_id"], ["archivos.id"], name="fk_versiones_archivo", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"], name="fk_versiones_autor", ondelete="RESTRICT"),
        sa.UniqueConstraint("archivo_id", "numero_version", name="uq_versiones_archivo_numero"),
        sa.CheckConstraint("tamano_bytes > 0", name="chk_tamano_positivo"),
        sa.CheckConstraint("numero_version > 0", name="chk_numero_version_positivo"),
    )

    # Llave foranea diferida para version_vigente_id en archivos
    op.create_foreign_key(
        "fk_archivos_version_vigente",
        "archivos",
        "versiones",
        ["version_vigente_id"],
        ["id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )

    # 7. Tabla permisos
    op.create_table(
        "permisos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("carpeta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rol_tipo", postgresql.ENUM("administrador", "editor", "revisor", "lector", name="rol_usuario_enum", create_type=False), nullable=True),
        sa.Column("nivel_acceso", postgresql.ENUM("lectura", "edicion", "administracion", name="nivel_acceso_enum", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["carpeta_id"], ["carpetas.id"], name="fk_permisos_carpeta", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_permisos_usuario", ondelete="CASCADE"),
        sa.CheckConstraint(
            "(usuario_id IS NOT NULL AND rol_tipo IS NULL) OR (usuario_id IS NULL AND rol_tipo IS NOT NULL)",
            name="chk_permiso_sujeto",
        ),
    )

    # 8. Tabla bitacora
    op.create_table(
        "bitacora",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("entidad", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.String(100), nullable=True),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_bitacora_usuario", ondelete="SET NULL"),
    )

    # 9. Triggers de Inmutabilidad
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_prevenir_modificacion_inmutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Operación no permitida: los registros de % son estrictamente inmutables.', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_versiones_inmutables
        BEFORE UPDATE OR DELETE ON versiones
        FOR EACH ROW EXECUTE FUNCTION fn_prevenir_modificacion_inmutable();
    """)

    op.execute("""
        CREATE TRIGGER trg_bitacora_inmutable
        BEFORE UPDATE OR DELETE ON bitacora
        FOR EACH ROW EXECUTE FUNCTION fn_prevenir_modificacion_inmutable();
    """)

    # 10. Indices Optimizados
    op.create_index("idx_carpetas_padre", "carpetas", ["carpeta_padre_id", "en_papelera"])
    op.create_index("idx_archivos_carpeta", "archivos", ["carpeta_id", "en_papelera", "nombre"])
    op.create_index("idx_versiones_archivo_desc", "versiones", ["archivo_id", sa.text("numero_version DESC")])
    op.create_index("idx_versiones_sha256", "versiones", ["sha256_hash"])
    op.create_index(
        "idx_archivos_bloqueo_expirado",
        "archivos",
        ["bloqueo_expira_en"],
        postgresql_where=sa.text("bloqueado_por IS NOT NULL"),
    )
    op.create_index("idx_bitacora_timeline", "bitacora", [sa.text("created_at DESC"), "usuario_id"])
    op.execute("CREATE INDEX idx_archivos_nombre_trgm ON archivos USING GIN (nombre gin_trgm_ops);")


def downgrade() -> None:
    # Eliminar indices
    op.execute("DROP INDEX IF EXISTS idx_archivos_nombre_trgm;")
    op.drop_index("idx_bitacora_timeline", table_name="bitacora")
    op.drop_index("idx_archivos_bloqueo_expirado", table_name="archivos")
    op.drop_index("idx_versiones_sha256", table_name="versiones")
    op.drop_index("idx_versiones_archivo_desc", table_name="versiones")
    op.drop_index("idx_archivos_carpeta", table_name="archivos")
    op.drop_index("idx_carpetas_padre", table_name="carpetas")

    # Eliminar triggers y funcion
    op.execute("DROP TRIGGER IF EXISTS trg_bitacora_inmutable ON bitacora;")
    op.execute("DROP TRIGGER IF EXISTS trg_versiones_inmutables ON versiones;")
    op.execute("DROP FUNCTION IF EXISTS fn_prevenir_modificacion_inmutable;")

    # Eliminar FK diferida
    op.drop_constraint("fk_archivos_version_vigente", "archivos", type_="foreignkey")

    # Eliminar tablas
    op.drop_table("bitacora")
    op.drop_table("permisos")
    op.drop_table("versiones")
    op.drop_table("archivos")
    op.drop_table("carpetas")
    op.drop_table("usuarios")

    # Eliminar ENUMs
    op.execute("DROP TYPE IF EXISTS estado_revision_enum;")
    op.execute("DROP TYPE IF EXISTS nivel_acceso_enum;")
    op.execute("DROP TYPE IF EXISTS rol_usuario_enum;")
