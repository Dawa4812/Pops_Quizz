# Generated by Django 3.0.6 on 2020-05-21 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Quizz', '0004_auto_20200521_1245'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='isPublic',
            field=models.BooleanField(default=True),
        ),
    ]
