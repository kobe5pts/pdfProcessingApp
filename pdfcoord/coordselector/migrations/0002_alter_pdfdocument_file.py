# Generated by Django 4.2.13 on 2024-07-05 10:57

import coordselector.custom_storages
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coordselector', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdfdocument',
            name='file',
            field=models.FileField(storage=coordselector.custom_storages.UploadsStorage(), upload_to=''),
        ),
    ]
