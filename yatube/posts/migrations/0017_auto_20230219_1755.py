# Generated by Django 2.2.16 on 2023-02-19 17:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0016_auto_20230219_1751'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='follow',
            name='unique_name_description',
        ),
    ]