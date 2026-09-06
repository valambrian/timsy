from django.db import migrations, models


def migrate_active_to_state(apps, schema_editor):
    Parent = apps.get_model('timsy', 'Parent')
    Parent.objects.filter(active=True).update(state='active')
    Parent.objects.filter(active=False).update(state='completed')


def reverse_state_to_active(apps, schema_editor):
    Parent = apps.get_model('timsy', 'Parent')
    Parent.objects.filter(state='active').update(active=True)
    Parent.objects.exclude(state='active').update(active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('timsy', '0021_activity_is_placeholder'),
    ]

    operations = [
        migrations.AddField(
            model_name='parent',
            name='state',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('active', 'Active'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='active',
                max_length=9,
            ),
        ),
        migrations.RunPython(migrate_active_to_state, reverse_state_to_active),
        migrations.RemoveField(
            model_name='parent',
            name='active',
        ),
    ]
