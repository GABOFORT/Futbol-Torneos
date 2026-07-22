from django.db import migrations


def fix_staff_access(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')
    Usuario.objects.filter(is_superuser=False).exclude(role='superadmin').update(is_staff=False)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_staff_access, noop),
    ]
