from sqlalchemy.orm import Session

from app.models.framework_mapping import FrameworkMapping


def create_framework_mapping(
    db: Session,
    mapping
):
    new_mapping = FrameworkMapping(
        cycle_id=mapping.cycle_id,
        framework_name=mapping.framework_name,
        control_name=mapping.control_name,
        status=mapping.status
    )

    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)

    return new_mapping