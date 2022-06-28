import enum
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import inspect

from app import db


class CommitMixin:

    def commit(self):
        fail_reason = None
        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError as ex:
            db.session.rollback()
            fail_reason = ex
        except ValueError as ex:
            db.session.rollback()
            fail_reason = ex
        finally:
            return self, fail_reason


class DeleteMixin:
    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return None
        except SQLAlchemyError as ex:
            db.session.rollback()
            return ex
        except ValueError as ex:
            db.session.rollback()
            return ex


class SyntheticKeyMixin:
    @declared_attr
    def pk(self):
        for base in self.__mro__[1:-1]:
            if getattr(base, '__table__', None) is not None:
                t = db.ForeignKey(base.pk)
                break
        else:
            t = db.Integer

        return db.Column('id', t, primary_key=True)


class HistoryMixin:

    @property
    def history(self):
        state = inspect(self)

        changes = {}

        for attr in state.attrs:
            hist = state.get_history(attr.key, True)

            if not hist.has_changes():
                continue

            old_value = hist.deleted[0] if hist.deleted else None
            new_value = hist.added[0] if hist.added else None
            if old_value != new_value:
                changes[attr.key] = [old_value, new_value]

        return changes


class OrderMixin:
    order_num = db.Column(db.Integer(), nullable=True)


class UtcCreatedMixin:
    created = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)


class UserType(enum.Enum):
    lessor = 0
    renter = 1


class Code(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, ):
    __tablename__ = 'verification_codes'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    target = db.Column(db.String(), nullable=False)
    code = db.Column(db.String(), nullable=False)
    used = db.Column(
        db.Boolean(),
        default=False,
        nullable=False
    )
    expired_at = db.Column(
        db.DateTime(),
        nullable=True,
        default=lambda: datetime.utcnow() + timedelta(minutes=5)
    )


class User(db.Model, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'users'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []

    pk = db.Column('id', db.Integer(), primary_key=True, index=True, unique=True, nullable=False)

    tel = db.Column(db.String(), nullable=True)
    login = db.Column(db.String(), nullable=True)
    password = db.Column(db.String(), nullable=True)
    is_admin = db.Column(db.Boolean(), nullable=False, default=False)
    user_type = db.Column(db.Enum(UserType), nullable=True)
    name = db.Column(db.String(), nullable=True)
    avatar = db.Column(db.String(), nullable=True)

    token_pairs = db.relationship('TokenPair', back_populates='user')
    devices = db.relationship('Device', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')
    reviews = db.relationship('Review', back_populates='user', cascade="all, delete-orphan")
    rooms = db.relationship('Room', back_populates='user', cascade="all, delete-orphan")
    block_lists_subject = db.relationship('BlockLo', back_populates='subject', cascade="all, delete-orphan",
                                          foreign_keys='[BlockList.subject_id]')
    block_lists_object = db.relationship('BlockLo', back_populates='object_', cascade="all, delete-orphan",
                                         foreign_keys='[BlockList.object_id]')
    rents = db.relationship('Rent', back_populates='user', cascade="all, delete-orphan", lazy='dynamic')


class BlockList(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'block_lists'

    class Meta:
        enable_in_sai = True

    object_id = db.Column(db.Integer, db.ForeignKey(User.pk), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey(User.pk), nullable=False)

    object_ = db.relationship('User', back_populates='block_lists_object')
    subject = db.relationship('User', back_populates='block_lists_subject')


class Token(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, ):
    __tablename__ = 'tokens'

    class Meta:
        enable_in_sai = True

    value = db.Column(db.String(), nullable=False)
    expires_at = db.Column(db.DateTime(), nullable=False)

    as_refresh = db.relationship(
        'TokenPair',
        uselist=False,
        back_populates='refresh_token',
        foreign_keys='[TokenPair.refresh_token_id]'
    )
    as_access = db.relationship(
        'TokenPair',
        uselist=False,
        back_populates='access_token',
        foreign_keys='[TokenPair.access_token_id]'

    )


class TokenPair(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, ):
    __tablename__ = 'token_pairs'

    class Meta:
        enable_in_sai = True

    device = db.Column(db.String(), nullable=True)

    user_id = db.Column(db.Integer(), db.ForeignKey(User.pk), nullable=True)

    refresh_token_id = db.Column(db.Integer, db.ForeignKey(Token.pk), nullable=True)
    access_token_id = db.Column(db.Integer(), db.ForeignKey(Token.pk), nullable=True)

    user = db.relationship(User, back_populates='token_pairs')

    refresh_token = db.relationship(
        Token,
        foreign_keys=[refresh_token_id],
        back_populates='as_refresh'
    )
    access_token = db.relationship(
        Token,
        foreign_keys=[access_token_id],
        back_populates='as_access'
    )


class Device(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, ):
    __tablename__ = 'devices'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    user_id = db.Column(db.Integer(), db.ForeignKey(User.pk), nullable=False)
    firebase_id = db.Column(db.String(), nullable=True)
    user_agent = db.Column(db.String(), nullable=True)
    enable_notification = db.Column(db.Boolean(), nullable=False, default=True)

    user = db.relationship(User, back_populates='devices')


class Notification(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, ):
    __tablename__ = 'notifications'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    text = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    read = db.Column(db.Boolean(), nullable=False, default=False)

    user_id = db.Column(db.Integer(), db.ForeignKey(User.pk), nullable=False)

    user = db.relationship(User, back_populates='notifications')


class Amenity(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin):
    __tablename__ = 'amenities'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    name = db.Column(db.String, nullable=False)
    icon = db.Column(db.String, nullable=False)

    amenity_rooms = db.relationship('RoomAmenity', back_populates='amenity', cascade="all, delete-orphan")


class Room(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'rooms'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    humans_count = db.Column(db.Integer, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Integer, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey(User.pk), nullable=False)

    user = db.relationship(User, back_populates='rooms', cascade="all, delete-orphan")
    room_amenities = db.relationship('RoomAmenity', back_populates='room', cascade="all, delete-orphan")
    attachments = db.relationship('Attachment', back_populates='room', cascade="all, delete-orphan")
    rents = db.relationship('Rent', back_populates='room', cascade="all, delete-orphan", lazy='dynamic')


class RoomAmenity(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'amenities_rooms'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    amenity_id = db.Column(db.Integer, db.ForeignKey(Amenity.pk), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey(Room.pk), nullable=False)

    amenity = db.relationship(Amenity, back_populates='amenity_rooms')
    room = db.relationship(Room, back_populates='room_amenities')


class Attachment(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'attachments'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    link = db.Column(db.String, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey(Room.pk), nullable=False)

    room = db.relationship(Room, back_populates='attachments')


class Rent(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):

    __tablename__ = 'rents'

    class Meta:
        enable_in_sai = True

    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    tel = db.Column(db.String, nullable=False)
    comment = db.Column(db.String, nullable=True)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime,nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey(Room.pk), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.pk), nullable=False)

    room = db.relationship(Room, back_populates='rents')
    user = db.relationship(User, back_populates='rents')
    room_renters = db.relationship('RoomRenter', back_populates='room', cascade="all, delete-orphan")
    reviews = db.relationship('Review', back_populates='rent', cascade="all, delete-orphan", lazy='dynamic')


class RoomRenter(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):

    __tablename__ = 'room_renters'

    class Meta:
        enable_in_sai = True

    grown_ups_count = db.Column(db.String, nullable=False)
    children_count = db.Column(db.String, nullable=False)

    rent_id = db.Column(db.Integer, db.ForeignKey(Rent.pk),nullable=False)
    
    rent = db.relationship(Rent, back_populates='room_renters')


class Review(db.Model, SyntheticKeyMixin, DeleteMixin, CommitMixin, HistoryMixin, UtcCreatedMixin):
    __tablename__ = 'reviews'

    class Meta:
        enable_in_sai = True
        column_searchable_list = []
        column_filters = []

    text = db.Column(db.String, nullable=True)
    rate = db.Column(db.Integer, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey(User.pk), nullable=False)
    rent_id = db.Column(db.Integer, db.ForeignKey(Rent.pk), nullable=False)

    user = db.relationship(User, back_populates='reviews')
    rent = db.relationship(Rent, back_populates='reviews')
