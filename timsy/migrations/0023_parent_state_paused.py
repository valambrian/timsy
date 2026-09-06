from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timsy', '0022_parent_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parent',
            name='state',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('active', 'Active'),
                    ('paused', 'Paused'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='active',
                max_length=9,
            ),
        ),
    ]
