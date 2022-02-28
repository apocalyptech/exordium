from django.apps import AppConfig


class ExordiumConfig(AppConfig):
    name = 'exordium'

    # https://docs.djangoproject.com/en/4.0/releases/3.2/#customizing-type-of-auto-created-primary-keys
    # If we allow the BigAutoField change to happen, the migration ends up dropping+recreating
    # foreign keys, and the migration takes a lot longer than I'd like (though admittedly it's
    # maybe dozens of seconds at most).  Anyway, let's just prevent the change.
    default_auto_field = 'django.db.models.AutoField'

