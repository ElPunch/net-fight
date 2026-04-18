# Migracion: agrega el modelo Fight (enfrentamientos).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Fight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orden', models.PositiveIntegerField(default=1)),
                ('titulo', models.CharField(blank=True, help_text='Nombre opcional de la pelea (ej: Pelea estelar)', max_length=200)),
                ('notas', models.TextField(blank=True, null=True)),
                ('evento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enfrentamientos', to='events.event')),
                ('peleador_a', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='peleas_como_a', to=settings.AUTH_USER_MODEL)),
                ('peleador_b', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='peleas_como_b', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Enfrentamiento',
                'verbose_name_plural': 'Enfrentamientos',
                'ordering': ['evento', 'orden'],
            },
        ),
        migrations.AddConstraint(
            model_name='fight',
            constraint=models.CheckConstraint(
                check=models.Q(('peleador_a', models.F('peleador_b')), _negated=True),
                name='fight_distinct_fighters',
            ),
        ),
    ]
