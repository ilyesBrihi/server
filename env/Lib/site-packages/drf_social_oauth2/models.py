from django.db import models
from django.db.models import CharField, Model


class MultiFactorAuth(Model):
    id = models.BigAutoField(primary_key=True)
    token = CharField(max_length=255, unique=False, blank=False, null=False, db_index=True)
    backend = CharField(max_length=100, unique=False, blank=False, null=False)
    client_id = CharField(max_length=100, unique=False)
    client_secret = CharField(max_length=255, unique=False)
    code = CharField(max_length=6, blank=False, null=False, db_index=True)

    expires = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # @todo - define expiration of token
    def is_expired(self):
        pass

    def validate(self):
        pass
