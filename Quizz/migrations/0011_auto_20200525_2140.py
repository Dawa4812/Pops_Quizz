# Generated by Django 3.0.6 on 2020-05-25 21:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Quizz', '0010_auto_20200523_1839'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='has_answered',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='game',
            name='uuid',
            field=models.CharField(default='CCBDED33', editable=False, max_length=255, unique=True),
        ),
    ]
