GitHub_CONFIG = {
    'token': [''],
    'per_page': 100,
    'max_page': 25

}

PATH_FILE = {
    'data': './data/'
}

LIBRARY_CONFIG = {
    'import': [
        'comet_ml',
        'whylogs',
        'wandb',
        'tensorboard',
        'mlflow',
        'tensorflow',
        'neptune',
        'dowel',
        'sacred',
        'ml_logger',
        'logging',
        'warnnings'
    ]
}

LOGGING_CONFIG = {
    'logging': [
        'logging.basicConfig',
        'logging.getLogger',
        'logging.config.fileConfig',
        'logging.Formatter',
        'logging.config.dictConfig',
        'logging.disable',
        'logging.getLevelName',
        'log.getLogger',
        'logging.shutdown',
        'logger.setLevel',
        'logger.addHandler',
        'logger.removeHandler',
        'logger.propagate',
        'logging.FileHandler',
        'logger.handlers',
        'logging.addLevelName',
        'logging.StreamHandler',
        'basicConfig',
        'inference_logger',
        'logging.getLogRecordFactory',
        'logging.log',
        'logging.Logger',
        'logging.LogRecord',
        'logging.Logger',
        'test_util',
        'util',
        'logging.captureWarnings'
    ],
    'wandb': [
        'wandb.init',
        'wandb.login',
        'wandb.setup',
        'wandb.require',
        'wandb.config.update',
        'wandb.finish',
        'wandb.Api()'
    ],
    'mlflow': [
        'mlflow.set_tracking_uri',
        'mlflow.set_experiment',
        'mlflow.start_run',
        'mlflow.end_run',
        'mlflow.create_experiment',
        'mlflow.set_registry_uri',
        'mlflow.set_tag',
        'mlflow.delete_tag',
        'mlflow.set_tags',
        'mlflow.get_tag',
        'mlflow.get_run',
        'mlflow.get_experiment',
        'mlflow.get_tracking_uri',
        'mlflow.active_run',
        'mlflow.last_active_run',
    ],
    'tensorboard': [
        'tensorboard.program.TensorBoard',
        'tensorboard.summary.create_file_writer',
        'tensorboard.summary.experimental_setup',
        'tensorboard.summary.experimental_run',
        'tensorboard.default.get_logger',
        'plugin_util',
        'context.RequestContext',
        'default.get_assets_zip_provider',
        'db.Connection',
        'db.Schema',
        'data_compat.migrate_value',
        'util.encode_png',
        'expand_dims',
        'random.categorical'
    ],
    'neptune': [
        'neptune.init',
        'neptune.init_run',
        'neptune.init_project',
        'neptune.new.init_run',
        'neptune.new.init_project',
        'neptune.login'
    ],
    'comet_ml': [
        'comet_ml.API',
        'comet_ml.config.get_config',
        'comet_ml.Experiment',
        'comet_ml.start',
        'comet_ml.init',
        'comet_ml.login'
    ],
    'whylogs': [
        'whylogs.init',
        'whylogs.get_or_create_session',
        'whylogs.logger.init',
        'whylogs.container.init_logger'
    ],
    'tensorflow': [
        'tf.summary'
    ],
    'dowel': [
        'dowel.set_logger',
        'tabular.prefix'
    ],
    'sacred': [
        'sacred.initialize'
    ],
    'ml_logger': [
        'ml_logger.logger.configure',
        'ml_logger.logger.set_directory',
        'logger.Prefix',
        'logger.Sync',
        'logger.configure',
        'logger.SyncContext',
        'logger.job_completed',
        'logger.job_errored',
        'logger.job_started',
        'logger.job_created',
        'logger.job_running'
    ],
    'warnings': [
        'warnings.filterwarnings',
        'warnings.simplefilter',
        'warnings.resetwarnings',
        'warnings.catch_warnings'
    ]
}

# Add your OpenAI API key here
OPENAI_API_KEY = "Here_is_your_openai_api_key"
