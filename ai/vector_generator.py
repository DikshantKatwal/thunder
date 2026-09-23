from django.apps import apps
from django.conf import settings
from django.db.models import ForeignKey, OneToOneField, ManyToManyField

# Audit/soft-delete columns that every model inherits from common.models
# (created_by, updated_by, deleted_by, is_deleted, deleted_at, ...). They're
# almost never relevant to a user's question but get repeated on every
# table, so dropping them here cuts the schema context sent to the LLM on
# every request by a large margin.
EXCLUDED_FIELD_NAMES = {
    "created_by",
    "updated_by",
    "deleted_by",
    "is_deleted",
    "deleted_at",
    "restored_at",
    "transaction_id",
}

# SHARED_APPS mostly hold cross-tenant data a tenant's chat must never see,
# but a few are pure *reference* lookups (currency/country codes, ...) with no
# tenant-scoped rows. Those live in the public schema, which is on the tenant
# connection's search_path anyway, and tenant tables FK straight into them
# (e.g. hr_employee_contract.currency_id -> utilities_countries.id), so a
# monetary amount can only be labelled with its currency by joining here.
# Keep this set to genuine lookup tables only.


def get_queryable_app_names():
    """Apps whose tables the AI pipeline may read: everything in a tenant's
    own schema, plus the shared reference lookups above."""
    tenant_apps = settings.TENANT_TYPES
    return set(tenant_apps) 

def get_database_schema():
    schema = []

    # TENANT_TYPES["tenant"]["APPS"] is the whitelist of what lives inside a
    # tenant's own schema; SHARED_REFERENCE_APPS adds the handful of safe
    # public-schema lookups.
    tenant_app_names = get_queryable_app_names()

    # include_auto_created=True - otherwise the implicit M2M join tables
    # (e.g. aauth_user_user_permissions, auth_group_permissions) are invisible
    # to the LLM entirely, so a question like "how many permissions does X
    # have" has no table to join through and can't be answered.
    for model in apps.get_models(include_auto_created=True):

        if model._meta.app_config.name not in tenant_app_names:
            continue

        table_name = model._meta.db_table

        fields = []
        relationships = []

        for field in model._meta.get_fields():

            # Ignore reverse relations and M2M for now
            if field.auto_created and not field.concrete:
                continue

            if field.many_to_many:
                continue

            if not field.concrete:
                continue

            if field.name in EXCLUDED_FIELD_NAMES:
                continue

            column_name = field.column
            field_type = field.get_internal_type()

            fields.append({
                "name": field.name,
                "column": column_name,
                "type": field_type,
                "primary_key": field.primary_key,
                "nullable": field.null,
            })

            # ForeignKey / OneToOne
            if field.is_relation and field.related_model:

                related_table = field.related_model._meta.db_table
                related_column = field.related_model._meta.pk.column

                relationships.append({
                    "column": column_name,
                    "related_table": related_table,
                    "related_column": related_column,
                })

        schema.append({
            "table": table_name,
            "fields": fields,
            "relationships": relationships,
        })

    return schema


def schema_to_text(schema):
    output = []

    for table in schema:
        output.append(f"TABLE: {table['table']}")
        output.append(f"MODEL: {table['model']}")

        output.append("COLUMNS:")

        for field in table["fields"]:
            output.append(
                f"- {field['name']} "
                f"({field['type']}) "
                f"nullable={field['nullable']}"
            )

        if table["relationships"]:
            output.append("RELATIONSHIPS:")

            for relation in table["relationships"]:
                output.append(
                    f"- {relation['field']} "
                    f"→ {relation['related_table']}"
                )

        output.append("")

    return "\n".join(output)


def build_sql_context(required_tables):
    schema = get_database_schema()

    output = []

    for table in schema:

        if table["table"] not in required_tables:
            continue

        output.append(f"TABLE: {table['table']}")
        output.append("COLUMNS:")

        for field in table["fields"]:

            column = field["column"]
            field_type = field["type"]

            extra = ""

            if field["primary_key"]:
                extra += " PRIMARY KEY"

            if field["nullable"]:
                extra += " NULL"

            output.append(
                f"- {column} {field_type}{extra}"
            )

        if table["relationships"]:

            output.append("RELATIONSHIPS:")

            for relation in table["relationships"]:

                output.append(
                    f"- {relation['column']} "
                    f"-> {relation['related_table']}."
                    f"{relation['related_column']}"
                )

        output.append("")

    return "\n".join(output)