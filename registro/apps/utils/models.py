""" DJANGO MODELS UTILITIES """

# DJANGO
from django.db import models

class BaseModel(models.Model):
    """
        Comparte los campos basicos con todos los modelos.
        Actua como una clase abstracta de los otros modelos. Esta clase añade
        los siguientes campos.
            + created (DateTime): Store the datetime the object was created.
            + modified (DateTime): Store the last datetime the object was modified.
    """

    created = models.DateTimeField(
        'Created at',
        auto_now_add = True,
        help_text='Fecha con la cual se creo el registro'
    )

    modified = models.DateTimeField(
        'modified at',
        auto_now = True,
        help_text='Fecha con la cual se modifico el objeto'
    )

    class Meta:
        abstract = True
        get_latest_by = 'created'
        ordering = ['-created','-modified']


class BaseModelDominioLADM(models.Model):
    """
        Comparte los campos basicos con todos los modelos.
        Actua como una clase abstracta de los otros modelos. Esta clase añade
        los siguientes campos de los dominios del LADM
    """
    thisclass = models.TextField(
        'Thisclass',
        help_text='',
        null= True
    )
    baseclass = models.TextField(
        'Baseclass',
        help_text='',
        null= True
    )
    itfcode = models.IntegerField(
        'Itfcode',
        help_text=''
    )
    ilicode = models.TextField(
        'Ilicode',
        help_text=''
    )
    seq = models.IntegerField(null= True)
    inactive = models.BooleanField(default=False)
    dispname = models.TextField(
        'Dispname',
        help_text=''
    )
    description = models.TextField(
        'Descripcion',
        help_text=''
    )
    created = models.DateTimeField(
        'Created at',
        auto_now_add = True,
        help_text='Fecha con la cual se creo el registro'
    )

    modified = models.DateTimeField(
        'modified at',
        auto_now = True,
        help_text='Fecha con la cual se modifico el objeto'
    )

    class Meta:
        abstract = True
        get_latest_by = 'created'
        ordering = ['-created','-modified']
    