from django.db import migrations, models
import django.db.models.deletion


def borrar_datos_antiguos(apps, schema_editor):
    Producto = apps.get_model('principal', 'Producto')
    Producto.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('principal', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(borrar_datos_antiguos, reverse_code=migrations.RunPython.noop),

        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Venta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('cliente', models.CharField(blank=True, default='Consumidor final', max_length=150)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ],
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='principal.venta')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='detalles', to='principal.producto')),
                ('cantidad', models.PositiveIntegerField()),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),

        migrations.AlterField(
            model_name='producto',
            name='nombre',
            field=models.CharField(max_length=150),
        ),
        migrations.AddField(
            model_name='producto',
            name='categoria',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='productos', to='principal.categoria'),
        ),
        migrations.AddField(
            model_name='producto',
            name='codigo',
            field=models.CharField(default='', max_length=50, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_compra',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_venta',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='producto',
            name='stock',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='producto',
            name='stock_minimo',
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.RemoveField(
            model_name='producto',
            name='precio',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='creado',
        ),
    ]
