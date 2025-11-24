from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from app.db.base import SessionLocal, engine
from app.db.models import Category, Model, Tariff


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if instance:
        return instance, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    session.add(instance)
    session.commit()
    return instance, True


def seed():
    session = SessionLocal()
    try:
        # Category
        cat, _ = get_or_create(session, Category, slug="image-to-video", title="Image to Video")

        # Model Veo 3.1
        get_or_create(
            session,
            Model,
            title="Veo 3.1",
            name="fal-ai/veo3.1/reference-to-video",
            description="Image to video generation",
            category_id=cat.id,
            cost_per_second=Decimal("0.20"),
            audio_cost_multiplier=Decimal("2.0"),
            cost_currency="USD",
            cost_type="second",
            format_from="image",
            format_to="video",
            banner_image_url=None,
            hint="Лучше работает с высококачественными изображениями 1024x1024 и детальным prompt",
            options={
                "durationOptions": [5, 10, 15],
                "resolutionOptions": ["720p", "1080p"],
                "aspectRatioOptions": ["16:9", "9:16", "1:1"],
                "generateAudio": True,
                "negativePrompt": True
            },
            max_file_count=5,
        )

        # Tariffs
        get_or_create(session, Tariff, name="trial", title="Пробный", monthly_tokens=25, cost_rub=0, currency="RUB")
        get_or_create(session, Tariff, name="basic", title="Базовый", monthly_tokens=600, cost_rub=499, currency="RUB")
        get_or_create(session, Tariff, name="pro", title="Про", monthly_tokens=1300, cost_rub=999, currency="RUB")

        print("Seed completed")
    finally:
        session.close()


if __name__ == "__main__":
    seed()

