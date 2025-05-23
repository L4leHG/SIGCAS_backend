# Generated by Django 5.2 on 2025-05-03 20:29

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permisos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Fecha con la cual se creo el registro', verbose_name='Created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Fecha con la cual se modifico el objeto', verbose_name='modified at')),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Fecha con la cual se creo el registro', verbose_name='Created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Fecha con la cual se modifico el objeto', verbose_name='modified at')),
                ('name', models.CharField(max_length=150)),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Fecha con la cual se creo el registro', verbose_name='Created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Fecha con la cual se modifico el objeto', verbose_name='modified at')),
                ('email', models.EmailField(error_messages={'Unique': 'El usuario con este email ya existe'}, max_length=254, unique=True, verbose_name='direccion electronica')),
                ('phone_number', models.CharField(blank=True, max_length=17)),
                ('is_client', models.BooleanField(default=True, help_text='Ayuda a identificar usuarios y realizar queries. ', verbose_name='Status del usuario')),
                ('is_verified', models.BooleanField(default=False, help_text='Configurado a verdadero cuando el usuario ha verificado su direccion de correo electronico', verbose_name='verificado')),
                ('activation_token_created', models.DateTimeField(blank=True, null=True)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='SubidaDiaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Fecha con la cual se creo el registro', verbose_name='Created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Fecha con la cual se modifico el objeto', verbose_name='modified at')),
                ('fecha', models.DateField(default=django.utils.timezone.now)),
                ('cantidad', models.IntegerField(default=0)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created', '-modified'],
                'get_latest_by': 'created',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Rol_predio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='Fecha con la cual se creo el registro', verbose_name='Created at')),
                ('modified', models.DateTimeField(auto_now=True, help_text='Fecha con la cual se modifico el objeto', verbose_name='modified at')),
                ('is_activate', models.BooleanField(default=False, help_text='Permite conocer que roles estan activos para cada usuario. ', verbose_name='Status del rp')),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='users.rol')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
                'indexes': [models.Index(fields=['user'], name='users_rol_p_user_id_e6f387_idx')],
            },
        ),
    ]
