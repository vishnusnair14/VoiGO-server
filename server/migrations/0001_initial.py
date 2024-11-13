# Generated by Django 5.1.1 on 2024-11-04 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OrderMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(default='None', max_length=256)),
                ('client_id', models.CharField(default='None', max_length=256)),
            ],
            options={
                'verbose_name': 'Order Map Register',
            },
        ),
        migrations.CreateModel(
            name='PartnerOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('partner_id', models.CharField(max_length=255, unique=True)),
                ('order', models.IntegerField()),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='PendingOBSOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(max_length=256, unique=True)),
                ('user_id_enc', models.CharField(default='None', max_length=256)),
                ('user_email', models.CharField(default='None', max_length=256)),
                ('user_phno_enc', models.CharField(default='None', max_length=256)),
                ('order_by_voice_doc_id', models.CharField(default='None', max_length=256)),
                ('order_by_voice_audio_ref_id', models.CharField(default='None', max_length=256)),
                ('shop_id', models.CharField(default='None', max_length=256)),
                ('shop_district', models.CharField(default='None', max_length=100)),
                ('shop_pincode', models.CharField(default='None', max_length=100)),
                ('curr_lat', models.CharField(blank=True, max_length=100, null=True)),
                ('curr_lon', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(default='pending', max_length=50)),
                ('dp_id', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order_type', models.CharField(default='unknown', max_length=256)),
            ],
            options={
                'verbose_name': 'Pending OBS Order Register',
            },
        ),
        migrations.CreateModel(
            name='PendingOBVOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(max_length=256, unique=True)),
                ('request_body', models.JSONField()),
                ('user_id_enc', models.CharField(default='None', max_length=256)),
                ('status', models.CharField(default='pending', max_length=50)),
                ('order_type', models.CharField(default='unknown', max_length=256)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Pending OBV Order Register',
            },
        ),
        migrations.CreateModel(
            name='TemporaryAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=13, unique=True)),
                ('address_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Temporary Address Register',
            },
        ),
        migrations.CreateModel(
            name='UploadedImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='images/')),
                ('name', models.CharField(default='None', max_length=256)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Uploaded Image Bucket',
            },
        ),
        migrations.CreateModel(
            name='WSChatRegister1',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.CharField(max_length=256, unique=True)),
                ('order_type', models.CharField(default='None', max_length=256)),
                ('order_client_id', models.CharField(default='None', max_length=256)),
                ('is_delivery_partner_assigned', models.BooleanField(default=False)),
                ('delivery_client_id', models.CharField(default='None', max_length=256)),
                ('is_order_client_connected', models.BooleanField(default=False)),
                ('order_client_id_for_ws', models.CharField(default='None', max_length=256)),
                ('is_delivery_client_connected', models.BooleanField(default=False)),
                ('delivery_client_id_for_ws', models.CharField(default='None', max_length=256)),
            ],
            options={
                'verbose_name': 'Chat Register',
            },
        ),
    ]