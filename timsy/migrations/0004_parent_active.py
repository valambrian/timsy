import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timsy', '0003_idealdaytemplaterecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='parent',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
