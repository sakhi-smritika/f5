from fastapi import APIRouter

from config.models import get_available_models, get_default_model_id

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models() -> dict:
    models = get_available_models()
    return {
        "default": get_default_model_id(),
        "models": [
            {
                "id": model.id,
                "label": model.label,
                "is_default": model.is_default,
            }
            for model in models
        ],
    }
