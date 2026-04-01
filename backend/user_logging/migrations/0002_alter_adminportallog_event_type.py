from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_logging', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminportallog',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('activity', 'Activity'),
                    ('login', 'Login'),
                    ('logout', 'Logout'),
                    ('login_failed', 'Login Failed'),
                ],
                max_length=20,
            ),
        ),
    ]
