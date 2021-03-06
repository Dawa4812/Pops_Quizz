# Generated by Django 3.0.6 on 2020-06-09 21:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Quizz', '0018_auto_20200606_1254'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='questions_answered',
            field=models.ManyToManyField(to='Quizz.Question'),
        ),
        migrations.AlterField(
            model_name='game',
            name='uuid',
            field=models.CharField(default='344F4933', editable=False, max_length=255, unique=True),
        ),
    ]
