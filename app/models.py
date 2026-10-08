from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ROLE_MEMBER = "member"
ROLE_ADMIN = "admin"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_site_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    memberships = db.relationship("Membership", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def membership_for(self, club: "Club") -> "Membership | None":
        return Membership.query.filter_by(user_id=self.id, club_id=club.id).first()

    def is_member_of(self, club: "Club") -> bool:
        return self.membership_for(club) is not None

    def can_manage(self, club: "Club") -> bool:
        if self.is_site_admin:
            return True
        membership = self.membership_for(club)
        return membership is not None and membership.role == ROLE_ADMIN


class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    memberships = db.relationship("Membership", back_populates="club", cascade="all, delete-orphan")
    events = db.relationship(
        "Event", back_populates="club", cascade="all, delete-orphan", order_by="Event.starts_at"
    )
    announcements = db.relationship(
        "Announcement",
        back_populates="club",
        cascade="all, delete-orphan",
        order_by="Announcement.created_at.desc()",
    )

    @property
    def member_count(self) -> int:
        return len(self.memberships)

    def upcoming_events(self):
        now = datetime.now()
        return [e for e in self.events if e.starts_at >= now]


class Membership(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "club_id", name="uq_membership"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("club.id"), nullable=False)
    role = db.Column(db.String(20), default=ROLE_MEMBER, nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="memberships")
    club = db.relationship("Club", back_populates="memberships")


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("club.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(200), nullable=False, default="")
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    capacity = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    club = db.relationship("Club", back_populates="events")
    rsvps = db.relationship("RSVP", back_populates="event", cascade="all, delete-orphan")

    @property
    def attendee_count(self) -> int:
        return len(self.rsvps)

    @property
    def is_full(self) -> bool:
        return self.capacity is not None and self.attendee_count >= self.capacity

    def has_rsvp(self, user) -> bool:
        return any(r.user_id == user.id for r in self.rsvps)


class RSVP(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "event_id", name="uq_rsvp"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")
    event = db.relationship("Event", back_populates="rsvps")


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("club.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    club = db.relationship("Club", back_populates="announcements")
    author = db.relationship("User")
