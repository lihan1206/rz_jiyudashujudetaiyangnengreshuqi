from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, HealthAssessment, User
from app.schemas import ReportItem

router = APIRouter(prefix="/reports", tags=["分析报告"])


@router.get("/weekly", response_model=list[ReportItem])
def weekly_report(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ReportItem]:
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=6)

    report: list[ReportItem] = []
    for offset in range(7):
        day_start = (start_time + timedelta(days=offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        avg_score = (
            db.query(func.avg(HealthAssessment.health_score))
            .filter(
                and_(
                    HealthAssessment.assessment_time >= day_start,
                    HealthAssessment.assessment_time < day_end,
                )
            )
            .scalar()
            or 0
        )

        high_risk_count = (
            db.query(func.count(HealthAssessment.id))
            .filter(
                and_(
                    HealthAssessment.assessment_time >= day_start,
                    HealthAssessment.assessment_time < day_end,
                    HealthAssessment.risk_level == "high",
                )
            )
            .scalar()
            or 0
        )

        alarm_count = (
            db.query(func.count(Alarm.id))
            .filter(and_(Alarm.created_at >= day_start, Alarm.created_at < day_end))
            .scalar()
            or 0
        )

        report.append(
            ReportItem(
                date=day_start.strftime("%Y-%m-%d"),
                avg_health_score=round(float(avg_score), 2),
                high_risk_count=high_risk_count,
                alarm_count=alarm_count,
            )
        )

    return report
