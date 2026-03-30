# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timsy', '0014_remove_blueprints_from_daily_plan'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='parent',
            name='abbreviation',
        ),
    ] 