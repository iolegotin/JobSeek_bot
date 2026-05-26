import pytest
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    weights_config = Column(JSON, nullable=True)

class MatchLog(Base):
    __tablename__ = 'match_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    vacancy_id = Column(Integer)
    action = Column(String)
    old_weights = Column(JSON)
    new_weights = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

@pytest.fixture
def db_session():
    """Создает чистую базу данных в памяти для КАЖДОГО теста отдельно"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

class TestFeedbackSvc:
    def test_like_feedback(self, db_session):
        user = User(id=1, weights_config={"python": 0.5, "sql": 0.3})
        db_session.add(user)
        db_session.commit()

        from app.core.services.feedback_svc import FeedbackService
        svc = FeedbackService(db_session)
        result = svc.process_feedback(1, 101, "like")

        assert result["status"] == "ok"
        # Перезапрашиваем юзера из базы, чтобы увидеть обновленные JSON данные
        db_session.refresh(user)
        assert user.weights_config["python"] == 1.0
        assert user.weights_config["sql"] == 0.8

        log = db_session.query(MatchLog).filter_by(user_id=1).first()
        assert log is not None
        assert log.action == "like"

    def test_dislike_feedback(self, db_session):
        user = User(id=2, weights_config={"java": 0.8, "c++": 0.6})
        db_session.add(user)
        db_session.commit()

        from app.core.services.feedback_svc import FeedbackService
        svc = FeedbackService(db_session)
        result = svc.process_feedback(2, 102, "dislike")

        assert result["status"] == "ok"
        db_session.refresh(user)
        assert user.weights_config["java"] == 0.3
        assert user.weights_config["c++"] == 0.1

        log = db_session.query(MatchLog).filter_by(user_id=2).first()
        assert log is not None
        assert log.action == "dislike"
