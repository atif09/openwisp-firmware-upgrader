from swapper import get_model_name as swapper_get_model_name
from swapper import load_model as swapper_load_model

APP_LABEL = "firmware_upgrader"


def load_model(model):
    return swapper_load_model(APP_LABEL, model)


def get_model_name(model):
    return swapper_get_model_name(APP_LABEL, model)
