from django.test import TestCase
from django.contrib.auth.models import User
from .models import Equipo, Jugador, Partido, Tarjeta, Estadistica, Torneo
from django.utils import timezone
from decimal import Decimal
from django.urls import reverse


class TarjetaModelTests(TestCase):

	def setUp(self):
		# Crear equipos, jugador y partido de prueba
		self.equipo1 = Equipo.objects.create(nombre='E1')
		self.equipo2 = Equipo.objects.create(nombre='E2')
		# Crear como staff para evitar que la señal cree automáticamente el perfil de Jugador
		user = User.objects.create_user(username='j1', password='pass', is_staff=True)
		self.jugador = Jugador.objects.create(user=user, nombre='Juan', apellido='Perez', equipo=self.equipo1)
		self.partido = Partido.objects.create(equipo_local=self.equipo1, equipo_visitante=self.equipo2, fecha=timezone.now())

	def test_segunda_amarilla_crea_roja(self):
		# Primera amarilla
		Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='amarilla', minuto=10)
		amarillas = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='amarilla').count()
		self.assertEqual(amarillas, 1)
		rojas = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='roja').count()
		self.assertEqual(rojas, 0)
		# Segunda amarilla -> debe crear una roja automáticamente
		Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='amarilla', minuto=50)
		amarillas = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='amarilla').count()
		# Aún puede haber 2 amarillas en el registro, pero debería existir 1 roja creada
		self.assertGreaterEqual(amarillas, 2)
		rojas = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='roja').count()
		self.assertEqual(rojas, 1)

	def test_no_permitir_tres_amarillas(self):
		# Crear dos amarillas
		Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='amarilla', minuto=5)
		Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='amarilla', minuto=30)
		# Intentar crear tercera amarilla debería lanzar ValidationError en clean()/save()
		from django.core.exceptions import ValidationError
		t = Tarjeta(partido=self.partido, jugador=self.jugador, tipo='amarilla', minuto=70)
		with self.assertRaises(ValidationError):
			t.full_clean()

	def test_no_permitir_mas_de_una_roja(self):
		# Crear una roja
		Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='roja', minuto=60)
		# Intentar crear otra roja debería validarse como error
		from django.core.exceptions import ValidationError
		t = Tarjeta(partido=self.partido, jugador=self.jugador, tipo='roja', minuto=80)
		with self.assertRaises(ValidationError):
			t.full_clean()

# Create your tests here.


class EstadisticasViewsTests(TestCase):

	def setUp(self):
		# Equipos
		self.e1 = Equipo.objects.create(nombre='E1v')
		self.e2 = Equipo.objects.create(nombre='E2v')
		# Users/jugadores
		user1 = User.objects.create_user(username='p1', password='pass')
		user2 = User.objects.create_user(username='p2', password='pass')
		# Si la señal creó ya el Jugador para usuarios no-staff, usar get_or_create
		self.j1, _ = Jugador.objects.get_or_create(user=user1, defaults={'nombre': 'Hector', 'apellido': 'Lugo', 'equipo': self.e1})
		self.j2, _ = Jugador.objects.get_or_create(user=user2, defaults={'nombre': 'Carlos', 'apellido': 'Diaz', 'equipo': self.e2})
		# Forzar equipo en caso de que la señal haya creado el perfil con el equipo por defecto
		if self.j1.equipo != self.e1:
			self.j1.equipo = self.e1
			self.j1.save()
		if self.j2.equipo != self.e2:
			self.j2.equipo = self.e2
			self.j2.save()
		# Partido
		self.partido = Partido.objects.create(equipo_local=self.e1, equipo_visitante=self.e2, fecha=timezone.now())

	def test_estadisticas_por_partido_suma_goles_numericos(self):
		# Crear una estadistica con goles=7 y relacion anotadores con j1
		e = Estadistica.objects.create(partido=self.partido, goles=7, asistencias=3)
		e.anotadores.add(self.j1)
		e.asistentes.add(self.j2)
		# Crear tarjetas manualmente
		Tarjeta.objects.create(partido=self.partido, jugador=self.j1, tipo='amarilla', minuto=12)
		Tarjeta.objects.create(partido=self.partido, jugador=self.j1, tipo='amarilla', minuto=45)

		# Llamar a la vista
		resp = self.client.get(reverse('estadisticas_por_partido', args=[self.partido.id]))
		self.assertEqual(resp.status_code, 200)
		datos = resp.context['datos']
		# Buscar el registro de j1
		d = next((x for x in datos if x['jugador'].id == self.j1.id), None)
		self.assertIsNotNone(d)
		# Debe sumar los 7 goles (campo numérico) y 2 amarillas
		self.assertEqual(d['goles'], 7)
		self.assertEqual(d['amarillas'], 2)

	def test_estadisticas_por_torneo_agregado(self):
		# Crear torneo con dos partidos
		t = Torneo.objects.create(nombre='T1', fecha_inicio='2025-01-01')
		p1 = Partido.objects.create(torneo=t, equipo_local=self.e1, equipo_visitante=self.e2, fecha='2025-04-01')
		p2 = Partido.objects.create(torneo=t, equipo_local=self.e2, equipo_visitante=self.e1, fecha='2025-04-08')
		# Estadisticas: j1 anota 2 en p1 y 1 en p2 (usando campos numéricos)
		e1 = Estadistica.objects.create(partido=p1, goles=2, asistencias=0)
		e1.anotadores.add(self.j1)
		e2 = Estadistica.objects.create(partido=p2, goles=1, asistencias=0)
		e2.anotadores.add(self.j1)
		# Tarjetas: una amarilla en p1 y una roja en p2
		Tarjeta.objects.create(partido=p1, jugador=self.j1, tipo='amarilla', minuto=10)
		Tarjeta.objects.create(partido=p2, jugador=self.j1, tipo='roja', minuto=55)

		resp = self.client.get(reverse('estadisticas_por_torneo', args=[t.id]))
		self.assertEqual(resp.status_code, 200)
		datos = resp.context['datos']
		d = next((x for x in datos if x['jugador'].id == self.j1.id), None)
		self.assertIsNotNone(d)
		# En total 3 goles, 1 amarilla, 1 roja
		self.assertEqual(d['goles'], 3)
		self.assertEqual(d['amarillas'], 1)
		self.assertEqual(d['rojas'], 1)

	def test_senal_estadistica_crea_tarjetas(self):
		# Crear una estadistica que amoneste y expulse jugadores
		est = Estadistica.objects.create(partido=self.partido, goles=0, asistencias=0)
		# Añadir j1 como amonestado y j2 como expulsado
		est.amonestados.add(self.j1)
		est.expulsados.add(self.j2)
		# Guardar para disparar la señal
		est.save()
		# Verificar que se crearon las tarjetas correspondientes
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla').exists())
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j2, tipo='roja').exists())

	def test_senal_estadistica_edicion_agrega_tarjeta(self):
		# Crear estadistica sin amonestados
		e = Estadistica.objects.create(partido=self.partido, goles=0, asistencias=0)
		# Inicialmente no hay tarjetas
		self.assertFalse(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1).exists())
		# Añadir j1 a amonestados y guardar (edición)
		e.amonestados.add(self.j1)
		e.save()
		# Debe haber creado la tarjeta amarilla
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla').exists())

	def test_senal_remove_elimina_tarjeta(self):
		# Crear estadistica con amonestado j1
		e = Estadistica.objects.create(partido=self.partido)
		e.amonestados.add(self.j1)
		e.save()
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla').exists())
		# Remover j1 de amonestados -> debe eliminar tarjeta
		e.amonestados.remove(self.j1)
		# Ahora la tarjeta debe existir pero marcada como anulada
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla', anulada=True).exists())

	def test_senal_clear_elimina_tarjetas(self):
		# Crear estadistica con varios amonestados y expulsados
		e = Estadistica.objects.create(partido=self.partido)
		e.amonestados.add(self.j1)
		e.expulsados.add(self.j2)
		e.save()
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla').exists())
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j2, tipo='roja').exists())
		# Clear ambos campos -> borrar tarjetas asociadas
		e.amonestados.clear()
		e.expulsados.clear()
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j1, tipo='amarilla', anulada=True).exists())
		self.assertTrue(Tarjeta.objects.filter(partido=self.partido, jugador=self.j2, tipo='roja', anulada=True).exists())

	def test_estadisticas_equipo_view(self):
		# Crear una entrada de estadistica y tarjeta para asegurar datos
		e = Estadistica.objects.create(partido=self.partido, goles=1, asistencias=0)
		e.anotadores.add(self.j1)
		Tarjeta.objects.create(partido=self.partido, jugador=self.j1, tipo='amarilla', minuto=22)
		resp = self.client.get(reverse('estadisticas_equipo'))
		self.assertEqual(resp.status_code, 200)
		datos = resp.context['estadisticas_jugadores']
		# Debe existir una entrada para j1 con claves esperadas
		rec = next((x for x in datos if x['jugador'].id == self.j1.id), None)
		self.assertIsNotNone(rec)
		self.assertIn('goles', rec)
		self.assertIn('tarjetas', rec)

	def test_agregar_pago_admin_view(self):
		# Crear un staff user y loguearlo
		staff = User.objects.create_user(username='staff', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		# Crear un pago mediante POST
		from django.core.files.uploadedfile import SimpleUploadedFile
		# usar metodo 'otro' con referencia para evitar requerir comprobante en este test
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '10.00',
			'metodo': 'otro',
			'referencia': 'REF-1234',
			'moneda': 'VES',
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		# Debe redirigir al dashboard
		self.assertEqual(resp.status_code, 302)
		# Y debe haberse creado el pago con el monto indicado
		from .models import Pago
		self.assertTrue(Pago.objects.filter(jugador=self.j1, monto=Decimal('10.00')).exists())

	def test_pago_efectivo_sin_comprobante_falla(self):
		staff = User.objects.create_user(username='staff2', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '5.00',
			'metodo': 'efectivo',
			'referencia': '',
			'moneda': 'VES',
			'next': 'dashboard'
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		# Ahora efectivo no requiere comprobante: debe crear el pago y redirigir
		self.assertEqual(resp.status_code, 302)
		from .models import Pago
		self.assertTrue(Pago.objects.filter(jugador=self.j1, monto='5.00').exists())

	def test_referencia_normalizacion_pago_movil_y_transferencia(self):
		# crear staff y loguearlo
		staff = User.objects.create_user(username='staff3', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		# pago_movil -> debe guardar últimos 4 dígitos
		from django.core.files.uploadedfile import SimpleUploadedFile
		# generar imagen PNG válida usando Pillow para asegurar formato y tamaño
		from PIL import Image
		from io import BytesIO
		buf = BytesIO()
		img = Image.new('RGB', (100, 100), color=(73, 109, 137))
		img.save(buf, format='PNG')
		buf.seek(0)
		comprobante_file = SimpleUploadedFile('img.png', buf.read(), content_type='image/png')
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '12.00',
			'metodo': 'pago_movil',
			'referencia': 'ABC-12345678',
			'comprobante': comprobante_file,
			'moneda': 'VES',
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		self.assertEqual(resp.status_code, 302)
		from .models import Pago
		p = Pago.objects.filter(jugador=self.j1, monto='12.00').first()
		self.assertIsNotNone(p)
		self.assertEqual(p.referencia, '5678')

		# transferencia -> debe guardar últimos 6 dígitos
		# otra imagen válida
		buf2 = BytesIO()
		img2 = Image.new('RGB', (120, 120), color=(200, 80, 100))
		img2.save(buf2, format='PNG')
		buf2.seek(0)
		comprobante_file2 = SimpleUploadedFile('img2.png', buf2.read(), content_type='image/png')
		data2 = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '20.00',
			'metodo': 'transferencia',
			'referencia': 'TRF-000123456789',
			'moneda': 'VES',
			'comprobante': comprobante_file2,
		}
		resp2 = self.client.post(reverse('agregar_pago_admin'), data2)
		self.assertEqual(resp2.status_code, 302)
		p2 = Pago.objects.filter(jugador=self.j1, monto='20.00').first()
		self.assertIsNotNone(p2)
		self.assertEqual(p2.referencia, '345678')

	def test_pago_efectivo_sin_referencia_con_comprobante_pasa(self):
		staff = User.objects.create_user(username='staff4', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		from django.core.files.uploadedfile import SimpleUploadedFile
		from PIL import Image
		from io import BytesIO
		buf = BytesIO()
		img = Image.new('RGB', (200, 200), color=(100, 150, 200))
		img.save(buf, format='PNG')
		buf.seek(0)
		comprobante_file = SimpleUploadedFile('efectivo.png', buf.read(), content_type='image/png')
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '15.00',
			'metodo': 'efectivo',
			'referencia': '',
			'moneda': 'VES',
			'comprobante': comprobante_file,
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		self.assertEqual(resp.status_code, 302)
		from .models import Pago
		self.assertTrue(Pago.objects.filter(jugador=self.j1, monto='15.00').exists())

	def test_pago_usd_sin_comprobante_falla(self):
		staff = User.objects.create_user(username='staff5', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '30.00',
			'metodo': 'transferencia',
			'referencia': 'REF-9999',
			'moneda': 'USD',
			'next': 'dashboard'
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		self.assertEqual(resp.status_code, 200)
		# Ahora el sistema no permite registrar Transferencia/Pago Móvil en USD
		self.assertContains(resp, 'No es posible registrar Pago Móvil o Transferencia en USD.', msg_prefix='Debe indicar error de moneda para USD en métodos no permitidos')

	def test_efectivo_usd_permitido(self):
		# staff can register efectivo in USD
		staff = User.objects.create_user(username='staff_usd', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '50.00',
			'metodo': 'efectivo',
			'referencia': '',
			'moneda': 'USD',
			'next': 'dashboard'
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		# debe redirigir al dashboard y crear el pago en USD
		self.assertEqual(resp.status_code, 302)
		from .models import Pago
		self.assertTrue(Pago.objects.filter(jugador=self.j1, monto='50.00', moneda='USD').exists())

	def test_agregar_equipos_a_torneo_existente(self):
		# Crear staff y loguearlo
		staff = User.objects.create_user(username='staff_torneos', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		# Crear torneo existente
		from .models import Torneo, Equipo
		t = Torneo.objects.create(nombre='Copa Test', fecha_inicio='2025-09-01')
		# Crear equipos a agregar
		e1 = Equipo.objects.create(nombre='Equipo A')
		e2 = Equipo.objects.create(nombre='Equipo B')
		# Hacer POST a la vista de editar_torneo para asignar equipos
		url = reverse('editar_torneo', args=[t.id])
		data = {
			'nombre': t.nombre,
			'fecha_inicio': str(t.fecha_inicio),
			'fecha_fin': '',
			'equipos': [str(e1.id), str(e2.id)],
		}
		resp = self.client.post(url, data)
		# Debe redirigir a lista_torneos
		self.assertEqual(resp.status_code, 302)
		# Refrescar torneo y verificar asociación M2M
		t.refresh_from_db()
		self.assertIn(e1, t.equipos.all())
		self.assertIn(e2, t.equipos.all())

	def test_referencia_mas_de_8_digitos_falla(self):
		# crear staff y loguearlo
		staff = User.objects.create_user(username='staff6', password='pw')
		staff.is_staff = True
		staff.save()
		self.client.force_login(staff)
		from django.core.files.uploadedfile import SimpleUploadedFile
		from PIL import Image
		from io import BytesIO
		buf = BytesIO()
		img = Image.new('RGB', (100, 100), color=(73, 109, 137))
		img.save(buf, format='PNG')
		buf.seek(0)
		comprobante_file = SimpleUploadedFile('img.png', buf.read(), content_type='image/png')
		# enviar referencia con 9 dígitos
		data = {
			'jugador': str(self.j1.id),
			'tipo': 'inscripcion',
			'monto': '40.00',
			'metodo': 'pago_movil',
			'referencia': '123456789',
			'comprobante': comprobante_file,
			'moneda': 'VES',
		}
		resp = self.client.post(reverse('agregar_pago_admin'), data)
		# debe fallar la validación y re-renderizar
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'La referencia no puede contener más de 6 dígitos.')
