from django.db import models
from django.contrib.gis.db import models as modelsGis
from registro.apps.login.models import Usuarios

# Create your models here.
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.



class CaracteristicasUnidadconstruccion(models.Model):
    identificador = models.CharField(max_length=10, blank=True, null=True)
    tipo_unidad_construccion = models.ForeignKey('CrUnidadconstrucciontipo',  on_delete=models.RESTRICT)
    total_plantas = models.IntegerField(blank=True, null=True)
    uso = models.ForeignKey('CrUsouconstipo',  on_delete=models.RESTRICT)
    anio_construccion = models.IntegerField(blank=True, null=True)
    area_construida = models.DecimalField(decimal_places=5, max_digits=20,blank=True, null=True)
    estado_conservacion = models.CharField(max_length=50, blank=True, null=True)
    local_id = models.CharField(max_length=100, blank=True, null=True)
    avaluo_unidad = models.BigIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'caracteristicas_unidadconstruccion'
    
    def __str__(self):
        return str(self.id)

class ColDocumentotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'col_documentotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class ColEstadodisponibilidadtipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["ilicode"]
        db_table = 'col_estadodisponibilidadtipo'

    def __str__(self):
        return self.ilicode


class ColFuenteadministrativatipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["ilicode"]
        db_table = 'col_fuenteadministrativatipo'

    def __str__(self):
        return self.ilicode


class ColInteresadotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'col_interesadotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class ColRelacionsuperficietipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'col_relacionsuperficietipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class ColUnidadadministrativabasicatipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'col_unidadadministrativabasicatipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode



class CrAutoreconocimientoetnicotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_autoreconocimientoetnicotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrCondicionprediotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_condicionprediotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrConstruccionplantatipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_construccionplantatipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrDerechotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_derechotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrDestinacioneconomicatipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_destinacioneconomicatipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrEstadotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_estadotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrMutaciontipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_mutaciontipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrPrediotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_prediotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrSexotipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_sexotipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrUnidadconstrucciontipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'cr_unidadconstrucciontipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class CrUsouconstipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    itfcode = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'cr_usouconstipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class Derecho(models.Model):
    tipo = models.ForeignKey('CrDerechotipo', on_delete=models.RESTRICT, db_column='tipo')
    fraccion_derecho = models.DecimalField(decimal_places=5, max_digits=20)
    naturaleza_juridica = models.CharField(max_length=100, blank=True, null=True)
    codigo_naturaleza_juridica = models.CharField(max_length=5, blank=True, null=True)
    fecha_anotacion = models.DateField(blank=True, null=True)
    interesado = models.ForeignKey('Interesado', on_delete=models.RESTRICT, blank=True, null=True)
    predio = models.ForeignKey('Predio', on_delete=models.RESTRICT, blank=True, null=True)
    comienzo_vida_util_version = models.DateField(auto_now=False,null=True)
    fin_vida_util_version = models.DateField(auto_now=False,blank=True, null=True)

    class Meta:
        db_table = 'derecho'


class EnteEmisortipo(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ente_emisortipo'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class EstadoAsignacion(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'estado_asignacion'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class EstadoRadicado(models.Model):
    t_id = models.AutoField(primary_key=True)
    ilicode = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'estado_radicado'
        ordering = ["ilicode"]

    def __str__(self):
        return self.ilicode


class FuenteAdministrativa(models.Model):
    tipo = models.ForeignKey('ColFuenteadministrativatipo', on_delete=models.RESTRICT)
    ente_emisor = models.ForeignKey('EnteEmisortipo', on_delete=models.RESTRICT)
    oficina_origen = models.IntegerField(blank=True, null=True)
    ciudad_origen = models.CharField(max_length=60, blank=True, null=True)
    estado_disponibilidad = models.ForeignKey('ColEstadodisponibilidadtipo', on_delete=models.RESTRICT)
    fecha_documento_fuente = models.DateField(blank=True, null=True)
    local_id = models.CharField(max_length=100, blank=True, null=True)
    numero_documento = models.CharField(
        max_length=1000, blank=True, null=True)


    class Meta:
        ordering = ["id"]
        db_table = 'fuente_administrativa'
    def __str__(self):
        return str(self.numero_documento)



class Interesado(models.Model):
    tipo_documento = models.ForeignKey('ColDocumentotipo', on_delete=models.RESTRICT)
    primer_nombre = models.CharField(max_length=100, blank=True, null=True)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100, blank=True, null=True)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    sexo = models.ForeignKey(CrSexotipo, on_delete=models.RESTRICT)
    autoreconocimientoetnico = models.ForeignKey('CrAutoreconocimientoetnicotipo', on_delete=models.RESTRICT, blank=True, null=True)
    autoreconocimientocampesino = models.BooleanField(blank=True, null=True)
    razon_social = models.CharField(max_length=255, blank=True, null=True)
    nombre = models.CharField(max_length=255, blank=True, null=True)
    tipo_interesado = models.ForeignKey('ColInteresadotipo', on_delete=models.RESTRICT, blank=True, null=True)
    numero_documento = models.CharField(max_length=255, blank=True, null=True)
    comienzo_vida_util_version = models.DateField(auto_now=False,null=True)
    fin_vida_util_version = models.DateField(auto_now=False,blank=True, null=True)
    local_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'interesado'


class InteresadoPredio(models.Model):
    interesado = models.ForeignKey('Interesado', on_delete=models.RESTRICT)
    predio = models.ForeignKey('Predio', on_delete=models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'interesado_predio'
        indexes = [
            models.Index(
                fields=['predio']),
        ]
    def __str__(self):
        if self.interesado.razon_social:
            return self.interesado.razon_social
        return '{0} {1} {2} {3}'.format(self.interesado.primer_nombre, self.interesado.segundo_nombre if self.interesado.segundo_nombre else '',
                                        self.interesado.primer_apellido, self.interesado.segundo_apellido if self.interesado.segundo_apellido else '')



class Predio(models.Model):
    departamento = models.CharField(max_length=2)
    municipio = models.CharField(max_length=3)
    codigo_orip = models.CharField(max_length=4, blank=True, null=True)
    matricula_inmobiliaria = models.IntegerField(blank=True, null=True)
    numero_predial_nacional = models.CharField(max_length=30)
    codigo_homologado = models.CharField(max_length=11)
    tipo_predio = models.ForeignKey('CrPrediotipo', on_delete=models.RESTRICT)
    condicion_predio = models.ForeignKey('CrCondicionprediotipo', on_delete=models.RESTRICT)
    destinacion_economica = models.ForeignKey('CrDestinacioneconomicatipo', on_delete=models.RESTRICT)
    area_catastral_terreno = models.DecimalField(decimal_places=5, max_digits=20, blank=True, null=True)
    vigencia_actualizacion_catastral = models.DateField(auto_now=False)
    estado = models.ForeignKey('CrEstadotipo',on_delete=models.RESTRICT)
    tipo = models.ForeignKey('ColUnidadadministrativabasicatipo', on_delete=models.RESTRICT)
    comienzo_vida_util_version = models.DateField(null=True,auto_now=False)
    fin_vida_util_version = models.DateField(auto_now=False,blank=True, null=True)
    direccion = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        ordering = ["numero_predial_nacional"]
        db_table = 'predio'
        indexes = [
            models.Index(fields=['estado', 'id']),
        ]
    def __str__(self):
        return str(self.numero_predial_nacional)
    

class PredioFuenteadministrativa(models.Model):
    fuenteadministrativa = models.ForeignKey(FuenteAdministrativa, on_delete=models.RESTRICT)
    predio = models.ForeignKey(Predio, models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'predio_fuenteadministrativa'

    def __str__(self):
        return str(self.id)


class PredioTramitecatastral(models.Model):
    predio = models.ForeignKey(Predio, models.RESTRICT)
    tramite_catastral = models.ForeignKey('TramiteCatastral', on_delete=models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'predio_tramitecatastral'
    def __str__(self):
        return str(self.id)


class PredioUnidadespacial(models.Model):
    terreno = models.ForeignKey('Terreno', on_delete=models.RESTRICT, blank=True, null=True)
    unidadconstruccion = models.ForeignKey('Unidadconstruccion', on_delete=models.RESTRICT, blank=True, null=True)
    predio = models.ForeignKey('Predio', on_delete=models.RESTRICT)
    local_id = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'predio_unidadespacial'
    def __str__(self):
        return str(self.id)        


class Radicado(models.Model):
    numero_radicado = models.CharField(max_length=30)
    fecha_radicado = models.DateField()
    estado_radicado = models.ForeignKey('EstadoRadicado', on_delete=models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'radicado'
        indexes = [
            models.Index(fields=[ "id", "numero_radicado"]),
        ]
    def __str__(self):
        return self.numero_radicado


class RadicadoPredioAsignado(models.Model):
    radicado = models.ForeignKey(Radicado, on_delete=models.RESTRICT)
    estado_asignacion = models.ForeignKey(EstadoAsignacion, on_delete=models.RESTRICT)
    usuario_analista = models.ForeignKey('login.Usuarios' , on_delete=models.RESTRICT, related_name='radicado_analista',blank=True, null=True)
    usuario_coordinador = models.ForeignKey('login.Usuarios' , on_delete=models.RESTRICT, related_name='radicado_coordinador', blank=True, null=True)
    mutacion = models.ForeignKey(CrMutaciontipo , on_delete=models.RESTRICT)
    predio = models.ForeignKey(Predio, on_delete=models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'radicado_predio_asignado'
    


class Terreno(modelsGis.Model):
    relacion_superficie = models.ForeignKey(ColRelacionsuperficietipo, on_delete=models.RESTRICT, blank=True, null=True)
    comienzo_vida_util_version = models.DateField(auto_now=False,null=True)
    fin_vida_util_version = models.DateField(auto_now=False,blank=True, null=True)
    geometria = modelsGis.MultiPolygonField(null=True, srid=9377)
    local_id = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'terreno'
    def __str__(self):
        return str(self.id)
    
class TerrenoZonas (models.Model):
    area_catastral_terreno = models.DecimalField(decimal_places=5, max_digits=20,blank=True, null=True)
    avaluo_terreno = models.BigIntegerField(blank=True, null=True)
    zona_fisica = models.IntegerField(blank=True, null=True)
    zona_geoeconomica = models.IntegerField(blank=True, null=True)
    terreno = models.ForeignKey('Terreno', on_delete=models.RESTRICT)

    class Meta:
        ordering = ["id"]
        db_table = 'terreno_zonas'

    def __str__(self):
        return str(self.id)

class TramiteCatastral(models.Model):
    mutacion = models.ForeignKey(CrMutaciontipo, on_delete=models.RESTRICT)
    numero_resolucion = models.CharField(max_length=30)
    fecha_resolucion = models.DateField(auto_now=False)
    fecha_inscripcion = models.DateField(auto_now=False)
    comienzo_vida_util_version = models.DateField(auto_now=False,null=True)
    fin_vida_util_version = models.DateField(auto_now=False,blank=True, null=True)
    radicado = models.CharField(max_length=30)
    radicado_asignado = models.ForeignKey('RadicadoPredioAsignado', on_delete=models.RESTRICT)


    class Meta:
        ordering = ["id"]
        db_table = 'tramite_catastral'
        indexes = [
            models.Index(fields=['numero_resolucion', 'fecha_resolucion', 'radicado', 'mutacion'])
        ]


class Unidadconstruccion(modelsGis.Model):
    tipo_planta = models.ForeignKey(CrConstruccionplantatipo, on_delete=models.RESTRICT)
    planta_ubicacion = models.IntegerField(blank=True, null=True)
    altura = models.DecimalField(decimal_places=5, max_digits=20, blank=True, null=True)
    caracteristicas_unidadconstruccion = models.ForeignKey(CaracteristicasUnidadconstruccion, on_delete=models.RESTRICT)
    comienzo_vida_util = models.DateField(auto_now=False)
    fin_vida_util = models.DateField(auto_now=False,blank=True, null=True)
    geometria = modelsGis.MultiPolygonField(null=True, srid=9377)
    local_id = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'unidadconstruccion'

    def __str__(self):
        return str(self.id)



class EstructuraAvaluo(models.Model):
    fecha_avaluo= models.DateField(auto_now=False)
    avaluo_catastral= models.BigIntegerField(blank=True, null=True)
    predio= models.ForeignKey('Predio', on_delete=models.RESTRICT)
    predio_tramitecatastral = models.ForeignKey ('PredioTramitecatastral', on_delete=models.RESTRICT)
    vigencia = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ["id"]
        db_table = 'estructura_avaluo'
        indexes = [
            models.Index(fields=['predio']),
        ]

    def __str__(self):
        return str(self.id)