import datetime
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.match_log import MatchLog
from sqlalchemy.orm.attributes import flag_modified


class FeedbackService:
    def __init__(self, session: Session):
        self.session = session

    def process_feedback(self, user_id: int, vacancy_id: int, action: str) -> dict:
        """
        Обрабатывает лайк/дизлайк на вакансию, корректируя веса и логируя действие.
        """
        user = self.session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        old_weights = user.weights_config.copy() if user.weights_config else {}
        new_weights = old_weights.copy()

        # Логика корректировки весов
        if action == "like":
            for key in new_weights:
                new_weights[key] = new_weights.get(key, 0) + 0.5
        elif action == "dislike":
            for key in new_weights:
                new_weights[key] = max(0, new_weights.get(key, 0) - 0.5)

        user.weights_config = new_weights
        flag_modified(user, 'weights_config')

        # Фиксация лога в match_logs
        log_entry = MatchLog(
            user_id=user_id,
            vacancy_id=vacancy_id,
            action=action,
            old_weights=old_weights,
            new_weights=new_weights,
            timestamp=datetime.datetime.now()
        )
        self.session.add(log_entry)

        return {"status": "ok", "new_weights": new_weights}
