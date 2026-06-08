import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Camera',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('url', models.URLField()),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='GestureEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('gesture_type', models.CharField(choices=[('wave', 'Wave'), ('fall', 'Fall Detected'), ('fight', 'Aggressive Movement')], max_length=20)),
                ('confidence', models.FloatField()),
                ('camera', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='surveillance.camera')),
            ],
        ),
    ]
