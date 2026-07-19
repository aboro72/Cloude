from django.db import migrations, connection


def add_fulltext_indexes(apps, schema_editor):
    indexes = [
        ("core_storagefile",      "ft_storagefile", "name"),
        ("news_newsarticle",      "ft_newsarticle",  "title, summary, content, tags"),
        ("sharing_teamsitenews",  "ft_teamsitenews", "title, content"),
        ("tasks_board_task",      "ft_task",         "title, description"),
    ]
    with connection.cursor() as cursor:
        for table, idx_name, cols in indexes:
            # Prüfe ob Index schon existiert
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE table_schema = DATABASE() "
                "AND table_name = %s AND index_name = %s",
                [table, idx_name],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    f"ALTER TABLE {table} ADD FULLTEXT INDEX {idx_name} ({cols})"
                )


def remove_fulltext_indexes(apps, schema_editor):
    indexes = [
        ("core_storagefile",     "ft_storagefile"),
        ("news_newsarticle",     "ft_newsarticle"),
        ("sharing_teamsitenews", "ft_teamsitenews"),
        ("tasks_board_task",     "ft_task"),
    ]
    with connection.cursor() as cursor:
        for table, idx_name in indexes:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE table_schema = DATABASE() "
                "AND table_name = %s AND index_name = %s",
                [table, idx_name],
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(f"ALTER TABLE {table} DROP INDEX {idx_name}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_notification_url_and_types'),
    ]

    operations = [
        migrations.RunPython(add_fulltext_indexes, remove_fulltext_indexes),
    ]
