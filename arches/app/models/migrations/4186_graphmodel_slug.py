# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2019-01-08 15:33
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('models', '4273_provisional_edit_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='graphmodel',
            name='slug',
            field=models.TextField(null=True, unique=True, validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
        ),
    ]
