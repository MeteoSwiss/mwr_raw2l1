from dynaconf import Dynaconf

cfg = Dynaconf(
    envvar_prefix='DYNACONF',
    settings_files=['settings.yaml', '.secrets.yaml'],
    environments=True,
    env=env,
)
