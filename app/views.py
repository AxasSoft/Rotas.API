import json
import os
import random
import re
from datetime import datetime, timedelta, time
from pathlib import Path
from time import sleep
from typing import Optional, List

import bcrypt
from flask import g, current_app, request, redirect
from flask import url_for
from sqlalchemy import desc, or_, and_, not_, func, cast, String
from greensms.client import GreenSMS

from app import app, schemas, request_validator, db
from app.models import Token, TokenPair, Device, User, Notification, Code, UserType, Attachment, Room, RoomAmenity, \
    Amenity, Rent, RoomRenter, Review, SavedRoom, BlockList
from utils.auth import auth
from utils.auth import gen_token
from utils.helpers import make_response
from utils.helpers import save_file
from utils.notifications import Notificator, DbConsumer, FbConsumer, TerminalConsumer
from utils.try_parse_int import try_parse_int
from utils.try_parse_float import try_parse_float

for_request = request_validator.validate
json_mt = ['application/json']
form_mt = ['multipart/form-data']

notificator = Notificator()
notificator.consumers = [
    TerminalConsumer(),
    DbConsumer(),
    FbConsumer(
        api_key=app.config.get('FIREBASE_API_KEY')
    )
]


def _dt(unix: Optional[int]):
    return datetime.fromtimestamp(unix) if unix is not None else None


def _unix(dt: Optional[datetime]) -> Optional[int]:
    return int(dt.timestamp()) if dt is not None else None


def _create_token_pair(user, device: Optional[str] = None):
    existing_tokens = list(token.value for token in Token.query.all())

    refresh_token_value = None
    access_token_value = None

    while refresh_token_value is None or refresh_token_value in existing_tokens:
        refresh_token_value = gen_token(64, '00')

    while access_token_value is None or access_token_value in existing_tokens:
        access_token_value = gen_token(64, '00')

    refresh_token = Token()
    refresh_token.value = refresh_token_value
    refresh_token.expires_at = datetime.utcnow() + timedelta(days=60)
    refresh_token.commit()

    access_token = Token()
    access_token.value = access_token_value
    access_token.expires_at = datetime.utcnow() + timedelta(hours=12)
    access_token.commit()

    pair = TokenPair()
    pair.user = user
    pair.device = device
    pair.access_token = access_token
    pair.refresh_token = refresh_token
    pair.commit()

    return access_token, refresh_token


def _update_settings(user, firebase_device_id, enable_notification, user_agent):
    device = Device.query.filter(Device.firebase_id == firebase_device_id).first()
    if device is not None:
        device.user_agent = user_agent
        device.enable_notification = enable_notification
        device.user = user
        device.commit()
    else:
        device = Device()
        device.firebase_id = firebase_device_id
        device.user_agent = user_agent
        device.enable_notification = enable_notification
        device.user = user
        device.commit()

    user.commit()


def _delete_user(user):
    for device in Device.query.filter(Device.user == user):
        db.session.delete(device)

    for notification in Notification.query.filter(Notification.user == user):
        db.session.delete(notification)

    for pair in TokenPair.query.filter(TokenPair.user == user):

        db.session.delete(pair)

        if pair.access_token is not None:
            db.session.delete(pair.access_token)
        if pair.refresh_token is not None:
            db.session.delete(pair.refresh_token)

    db.session.delete(user)

    db.session.commit()


def _get_user(user: User):
    return {
        'id': user.pk,
        'tel': user.tel,
        'login': user.login,
        'is_admin': user.is_admin,
        'type': user.user_type.value if user.user_type is not None else None,
        'name': user.name,
        'avatar': user.avatar
    }


def from_int_to_time(ts: Optional[int]) -> Optional[time]:
    if ts is None:
        return None

    hours, mod = divmod(ts, 3600)
    minutes, seconds = divmod(mod, 60)

    return time(hours, minutes, seconds)


def from_time_to_int(t: Optional[time]) -> Optional[int]:
    if t is None:
        return None

    return t.hour * 3600 + t.minute * 60 + t.second


@app.route('/tels/verify/', methods=['POST'])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.with_tel()
)
def generate_verification_code():
    body = g.received.body

    tel_white_list = current_app.config.get(
        'TEL_WHITE_LIST',
        ['79184167161', '79183657351', '79914202022', '79897687220']
    )

    if body.tel in tel_white_list:
        code_value = '8085'
    else:

        green_sms_user = current_app.config.get(
            'GREEN_SMS_LOGIN',
            'steptothemoney'
        )

        green_sms_password = current_app.config.get(
            'GREEN_SMS_PASSWORD',
            'Vi4t23EP'
        )

        client = GreenSMS(user=green_sms_user, password=green_sms_password)
        response = client.call.send(to=body.tel)
        code_value = response.code

    code = Code()
    code.code = code_value
    code.target = body.tel
    code.expired_at = datetime.utcnow() + timedelta(minutes=30)

    code.commit()

    return make_response(
        data={
            'code': code_value
        }
    )


@app.route('/siw/tel/', methods=['POST'])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.siw_tel()
)
def siw_tel():
    tel = g.received.body.tel

    codes = Code.query.filter(Code.target == tel).order_by(desc(Code.expired_at), Code.used).all()

    if len(codes) == 0:
        return make_response(
            status=401,
            message='Authorization denied',
            errors=[
                {
                    'code': 1,
                    'message': 'Verification code not created',
                    'source': 'tel',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='На указанный телефон не отправлялся код подтверждения'
        )

    codes_with_value = list(filter(lambda it: it.code == g.received.body.code, codes))

    if len(codes_with_value) == 0:
        return make_response(
            status=401,
            message='Authorization denied',
            errors=[
                {
                    'code': 2,
                    'message': 'Verification code dont match',
                    'source': 'tel',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='Код подтверждения не совпадает'
        )

    code = codes_with_value[0]

    if code.used:
        return make_response(
            status=401,
            message='Authorization denied',
            errors=[
                {
                    'code': 3,
                    'message': 'Verification code already used',
                    'source': 'tel',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='Код подтверждения уже использован'
        )

    if code.expired_at < datetime.utcnow():
        return make_response(
            status=401,
            message='Authorization denied',
            errors=[
                {
                    'code': 3,
                    'message': 'Verification code expired',
                    'source': 'tel',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='Время жизни кода подтверждения истекло'
        )

    code.used = True
    code.commit()

    actual_imei = request.headers.get('imei')
    actual_imei = g.received.body.get('imei', '1') if actual_imei is None else actual_imei

    user = User.query.filter(User.tel == tel).order_by(User.pk).first()

    if user is None:
        user = User()
        user.tel = tel
        user.commit()

    device = request.headers.get('device', None)
    user_agent = request.headers.get('User-Agent', None)
    enable_notifications = bool(request.headers.get('Enable-Notifications', True))

    _update_settings(
        user,
        user_agent=user_agent,
        firebase_device_id=device,
        enable_notification=enable_notifications,
    )

    db.add(user)
    db.session.commit()

    access_token, refresh_token = _create_token_pair(user, device)

    return make_response(
        status=200,
        data={
            'user': _get_user(user),
            'tokens': {
                'access': {
                    'value': access_token.value,
                    'expire_at': _unix(access_token.expires_at)
                },
                'refresh': {
                    'value': refresh_token.value,
                    'expire_at': _unix(refresh_token.expires_at)
                },
            }
        }
    )


@app.route('/siw/password/', methods=['POST'])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.siw_password()
)
def siw_password():
    login = g.received.body.login
    password = g.received.body.password

    user = User.query.filter(User.login == login).first()

    if user is None:
        return make_response(
            status=403,
            errors=[
                {
                    'code': 2,
                    'message': 'User do not exists',
                    'source': 'email',
                    'path': '$.body',
                    'additional': None
                }
            ]
        )

    if user.password is None or not bcrypt.checkpw(password.encode(), user.password.encode()):
        return make_response(
            status=403,
            errors=[
                {
                    'code': 2,
                    'message': 'Incorrect password',
                    'source': 'password',
                    'path': '$.body',
                    'additional': None
                }
            ]
        )

    device = request.headers.get('device', None)
    user_agent = request.headers.get('User-Agent', None)
    enable_notifications = bool(request.headers.get('Enable-Notifications', True))

    _update_settings(
        user,
        user_agent=user_agent,
        firebase_device_id=device,
        enable_notification=enable_notifications,
    )

    access_token, refresh_token = _create_token_pair(user, device)

    return make_response(
        status=200,
        data={
            'user': _get_user(user),
            'tokens': {
                'access': {
                    'value': access_token.value,
                    'expire_at': _unix(access_token.expires_at)
                },
                'refresh': {
                    'value': refresh_token.value,
                    'expire_at': _unix(refresh_token.expires_at)
                },
            }
        }
    )


@app.route('/notifications/', methods=['GET'])
@auth()
def get_notification():
    now = datetime.utcnow()

    data = [
        {
            'id': notification.pk,
            'text': notification.text,
            'created': _unix(notification.created_at),
            'is_read': notification.read
        }
        for notification in Notification.query.filter(
            or_(
                not_(Notification.read),
                now - Notification.created_at < timedelta(days=7),
            )
        ).order_by(Notification.read, desc(Notification.created_at))
    ]

    return make_response(
        data=data
    )


@app.route('/notifications/<int:notification_id>/is-read/', methods=['PUT'])
@auth()
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.editing_bool_mark()
)
def edit_readmark(notification_id):
    notification = Notification.query.get(notification_id)

    if notification is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Уведомление не найдено'
        )

    notification.read = g.received.body.value
    notification.commit()

    return make_response()


@app.route('/tokens/refresh/', methods=['POST'])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.renew_token()
)
def renew_token():
    refresh_token_value = g.received.body.refresh

    refresh_token = Token \
        .query \
        .filter(Token.value == refresh_token_value, Token.as_refresh != None) \
        .first()

    if refresh_token is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'token',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='Не удалось обновить токен'
        )

    now = datetime.utcnow()

    if refresh_token.expires_at < now:
        return make_response(
            status=422,
            errors=[
                {
                    'code': 1,
                    'message': 'Token expires',
                    'source': 'token',
                    'path': '$.body',
                    'additional': None
                }
            ],
            description='Не удалось обновить токен'
        )

    s = now - timedelta(seconds=1)

    refresh_token.expires_at = s
    refresh_token.commit()

    pair = refresh_token.as_refresh

    user = pair.user

    pair.access_token.expires_at = s
    pair.access_token.commit()

    device = request.headers.get('device', pair.device)

    access_token, refresh_token = _create_token_pair(user, device)

    return make_response(
        data={
            'access': {
                'value': access_token.value,
                'expire_at': _unix(access_token.expires_at)
            },
            'refresh': {
                'value': refresh_token.value,
                'expire_at': _unix(refresh_token.expires_at)
            },
        }
    )


@app.route('/settings/', methods=['PUT'])
@auth()
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.editing_device()
)
def edit_settings():
    body = g.received.body
    user = g.user

    user_agent = request.headers.get('User-Agent', None)
    firebase_id = body.device
    enable_notifications = body.enable_notifications

    _update_settings(
        user,
        user_agent=user_agent,
        firebase_device_id=firebase_id,
        enable_notification=enable_notifications,
    )

    return make_response()


@app.route('/profile/', methods=['GET'])
@auth()
def get_profile():
    return make_response(data=_get_user(g.user))


@app.route('/profile/', methods=['PUT'])
@auth()
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.edit_profile()
)
def edit_profile():
    user = g.user
    body = g.received.body

    if 'name' in body:
        user.name = body.name
    if 'type' in body:
        user.user_type = UserType(body.type) if body.type is not None else None

    return make_response(data=_get_user(user))


@app.route('/profile/avatar/', methods=['PUT'])
@auth()
@for_request(
    allowed_content_types=form_mt,
    body_fields=schemas.edit_profile_avatar()
)
def edit_profile_avatar():
    today = datetime.today()
    year = today.year
    month = today.month
    day = today.day

    directory = os.path.join("avatars", str(year), str(month), str(day))

    file = save_file(g.received.body.image, current_app.static_folder, directory)

    link = url_for('static', filename=file, _external=True)

    g.user.avatar = link

    db.session.add(g.user)
    db.session.commit()

    return make_response(data=_get_user(g.user))


@app.route('/profile/', methods=['DELETE'])
@auth()
def delete_user():
    user = g.user

    _delete_user(user)

    return make_response()


@app.route('/profile/avatar/', methods=['PUT'])
@auth()
@for_request(
    allowed_content_types=form_mt,
    body_fields=schemas.upload_attachment()
)
def upload_attachment():
    today = datetime.today()
    year = today.year
    month = today.month
    day = today.day

    directory = os.path.join("attachments", str(year), str(month), str(day))

    file = save_file(g.received.body.image, current_app.static_folder, directory)

    link = url_for('static', filename=file, _external=True)

    attachment = Attachment()
    attachment.link = link

    db.session.add(attachment)
    db.session.commit()

    return make_response(
        data={
            'id': attachment.id,
            'link': link
        }
    )


@app.route('/rooms/', methods=['POST'])
@auth(user_types=[UserType.lessor])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.create_room()
)
def create_room():
    room = Room()
    room.user = g.user
    body = g.received.body
    room.name = body.name
    room.address = body.address
    room.description = body.description
    room.price = body.price
    room.humans_count = body.humans_count
    room.number = body.number
    room.area = body.area

    for amenity_id in body.amenities:
        amenity = db.session(Amenity).get(amenity_id)
        if amenity is None:
            continue
        room_amenity = RoomAmenity()
        room_amenity.room = room
        room_amenity.amenity = amenity
        db.session.add(room_amenity)

    for attachment_id in body.attachments:
        attachment = db.session(Attachment).get(attachment_id)
        if attachment is None:
            continue
        attachment.room = room
        db.session.add(attachment)

    db.session.add(room)
    db.session.commit()

    return make_response(
        data={
            'id': room.id,
            'name': room.name,
            'address': room.address,
            'description': room.description,
            'price': room.price,
            'humans_count': room.humans_count,
            'number': room.number,
            'area': room.area,
            'amenities': [
                {
                    'id': ra.amenity.id,
                    'name': ra.amenity.name,
                    'icon': ra.amenity.icon
                }
                for ra in room.room_amenities
            ],
            'attachments': [
                att.link for att in room.attachments
            ]
        }
    )


@app.route('/rooms/<int:room_id>/rents/', methods=['POST'])
@auth(user_types=[UserType.renter])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.rent_room()
)
def rent_room(room_id):
    room = Room.query.get(room_id)
    if room is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 2,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Комната не найдена'
        )

    body = g.received.body

    rent = Rent()
    rent.room = room
    rent.user = g.user
    rent.comment = body.comment
    rent.start_at = _dt(body.start_at)
    rent.end_at = _dt(body.end_at)
    if 'tel' in body:
        rent.tel = body.tel
    else:
        rent.tel = g.user.tel

    if 'first_name' in body and 'last_name' in body:
        rent.first_name = body.first_name
        rent.last_name = body.last_name
    elif 'first_name' in body:
        rent.first_name = body.first_name
    elif 'last_name' in body:
        rent.last_name = body.last_name
    else:

        names = (g.user.name or '_').split(' ')

        if len(names) == 0:
            default_first_name = None
            default_last_name = None
        elif len(names) == 1:
            default_first_name = names[0]
            default_last_name = None
        else:
            default_first_name = names[1]
            default_last_name = names[0]

        rent.first_name = default_first_name
        rent.last_name = default_last_name

    for renter_info in body.renters:
        room_renter = RoomRenter()
        room_renter.rent = rent
        room_renter.children_count = renter_info['children_count']
        room_renter.grown_ups_count = renter_info['grown_ups_count']
        db.session.add(room_renter)

    db.session.add(Rent)
    db.session.commit()

    return make_response(
        data={
            'id': rent.pk,
            'first_name': rent.first_name,
            'last_name': rent.last_name,
            'tel': rent.tel,
            'comment': rent.comment,
            'start_at': _unix(rent.start_at),
            'end_at': _unix(rent.end_at)
        }
    )


@app.route('/lessors/me/rents/', methods=['GET'])
@auth(user_types=[UserType.lessor])
def get_rents():
    now = datetime.utcnow()

    rentals = {
        'new': [],
        'wait': [],
        'in_process': []
    }

    for rental in (db.session.query(Rent)
            .join(Room)
            .filter(Room.user == g.user, Rent.end_at >= now, Rent.verified != False)
            .all()
    ):

        rental_dict = {
            'id': rental.pk,
            'start_at': rental.start_at,
            'end_at': rental.end_at,
            'first_name': rental.first_name,
            'last_name': rental.last_name,
            'verified': rental.verified,
            'room': {
                'id': rental.room.pk,
                'name': rental.room.name,
                'attachments': [
                    attachment.link for attachment in rental.room.attachments
                ]
            },
            'renters': [
                {
                    'grown_ups_count': renter.grown_count,
                    'children_count': renter.children_count
                }
                for renter in rental.renters
            ]
        }

        if rental.verified is None and rental.start_at >= now:
            rentals['new'].append(rental_dict)
        if rental.verified and rental.start_at >= now:
            rentals['wait'].append(rental_dict)
        if rental.verified and rental.start_at < now:
            rentals['in_process'].append(rental_dict)

    return make_response(data=rentals)


@app.route('/rents/<rent_id>/', methods=['GET'])
@auth(user_types=[UserType.lessor])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.rent_room()
)
def edit_rent(rent_id):
    rent = Rent.query.get(rent_id)
    if rent is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Аренда не найдена'
        )

    rent.verified = g.rreceived.body.verified
    rent.commit()

    return make_response(
        data={
            'id': rent.pk,
            'start_at': rent.start_at,
            'end_at': rent.end_at,
            'first_name': rent.first_name,
            'last_name': rent.last_name,
            'verified': rent.verified,
            'room': {
                'id': rent.room.pk,
                'name': rent.room.name,
                'attachments': [
                    attachment.link for attachment in rent.room.attachments
                ]
            },
            'renters': [
                {
                    'grown_ups_count': renter.grown_count,
                    'children_count': renter.children_count
                }
                for renter in rent.renters
            ]
        }
    )


@app.route('/lessors/me/rents/history/', methods=['GET'])
@auth(user_types=[UserType.lessor])
def get_lessor_rent_history():
    now = datetime.utcnow()
    data = []
    for rental in (db.session.query(Rent)
            .join(Room)
            .filter(Room.user == g.user, Rent.end_at < now, Rent.verified == True)
            .all()
    ):
        data.append(
            {
                'id': rental.pk,
                'start_at': rental.start_at,
                'end_at': rental.end_at,
                'first_name': rental.first_name,
                'last_name': rental.last_name,
                'verified': rental.verified,
                'room': {
                    'id': rental.room.pk,
                    'name': rental.room.name,
                    'attachments': [
                        attachment.link for attachment in rental.room.attachments
                    ]
                },
                'renters': [
                    {
                        'grown_ups_count': renter.grown_count,
                        'children_count': renter.children_count
                    }
                    for renter in rental.renters
                ]
            }
        )


@app.route('/rents/<int:rent_id>/reviews/')
@auth(user_types=[UserType.lessor, UserType.renter])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.review_rent()
)
def review_rent(rent_id):
    rent = Rent.query.get(rent_id)
    if rent is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Аренда не найдена'
        )

    body = g.received.body
    review = Review()
    review.rate = body.rate
    review.text = body.text
    review.rent = rent
    review.user = g.user
    review.commit()

    return make_response(
        data={
            'id': review.id,
            'rate': review.rate,
            'text': review.text
        }
    )


@app.route('/renters/me/rooms/', methods=['GET'])
@auth(user_types=[UserType.renter])
def get_rooms():
    return make_response(
        data=[
            {
                'id': room.id,
                'name': room.name,
                'address': room.address,
                'attachments': [
                    attachment.link for attachment in room.attachments
                ],
                'amenities': [
                    {
                        'id': ra.amenity.id,
                        'name': ra.amenity.name,
                        'icon': ra.amenity.icon
                    }
                    for ra in room.room_amenities
                ],
                'rating': (
                    db.session
                        .query(func.avg(Review.rate))
                        .join(Rent).filter(Review.rate != None, Rent.room == room)
                        .scalar()
                )
            }
            for room in (
                db.session.query(Room)
                    .join(BlockList)
                    .filter(BlockList.subject != g.user, BlockList.object_ != g.user)
            )
        ]
    )


@app.route('/rooms/<int:room_id>/', methods=['GET'])
@auth(user_types=[UserType.renter])
def get_room(room_id):
    room = Room.query.get(room_id)
    if room is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Комната не найдена'
        )

    return make_response(
        data={
            'id': room.id,
            'name': room.name,
            'address': room.address,
            'description': room.description,

            'attachments': [
                attachment.link for attachment in room.attachments
            ],
            'amenities': [
                {
                    'id': ra.amenity.id,
                    'name': ra.amenity.name,
                    'icon': ra.amenity.icon
                }
                for ra in room.room_amenities
            ],
            'rating': (
                db.session
                    .query(func.avg(Review.rate))
                    .join(Rent).filter(Review.rate != None, Rent.room == room)
                    .scalar()
            ),
            'reviews': [
                {
                    'id': review.pk,
                    'text': review.text,
                    'rate': review.rate,
                    'user': {
                        'id': review.user.pk,
                        'name': review,
                        'rent': _unix(review.created)
                    }
                }
                for review in db.session.query(Review).join(Rent).filter(Rent.room == room)
            ]
        }
    )


@app.route('/rooms/<int:room_id>/is_saved/', methods=['PUT'])
@auth(user_types=[UserType.renter])
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.change_is_saved_mark()
)
def change_is_saved_mark(room_id):
    room = Room.query.get(room_id)
    if room is None:
        return make_response(
            status=404,
            errors=[
                {
                    'code': 1,
                    'message': 'Entity not found',
                    'source': 'pk',
                    'path': '$.url',
                    'additional': None
                }
            ],
            description='Комната не найдена'
        )

    saved_room = db.session.query(SavedRoom).filter(SavedRoom.user == g.user, SavedRoom.room == room).first()
    if saved_room is not None and not g.received.body.is_saved:
        saved_room.delete()
    elif saved_room is None and g.received.body.is_saved:
        saved_room = SavedRoom()
        saved_room.user = g.user
        saved_room.room = room
        saved_room.commit()

    return make_response()


@app.route('/rooms/<int:room_id>/is_saved/', methods=['GET'])
@auth(user_types=[UserType.renter])
def get_saved_rooms():
    return make_response(
        data=[
            {
                'id': room.id,
                'name': room.name,
                'address': room.address,
                'attachments': [
                    attachment.link for attachment in room.attachments
                ],
                'amenities': [
                    {
                        'id': ra.amenity.id,
                        'name': ra.amenity.name,
                        'icon': ra.amenity.icon
                    }
                    for ra in room.room_amenities
                ],
                'rating': (
                    db.session
                        .query(func.avg(Review.rate))
                        .join(Rent).filter(Review.rate != None, Rent.room == room)
                        .scalar()
                )
            }
            for room in db.session.query(Room).join(SavedRoom).filter(SavedRoom.user == g.user)
        ]
    )


@app.route('/block-list/')
@auth(user_types=[UserType.renter, UserType.lessor])
def get_block_list():
    return make_response(
        data=[
            {
                'id': user.id,
                'name': user.name,
                'tel': user.tel,
                'avatar': user.avatar
            }
            for user in db.session.query(User).join(BlockList.subject == g.user)
        ]
    )


@app.route('/users/<int:user_id>/in-block-list/')
@auth()
@for_request(
    allowed_content_types=json_mt,
    body_fields=schemas.change_in_block_list_mark()
)
def change_in_block_list_mark(user_id):
    user = db.session.query(User).get(user_id)

    in_block_list_mark = g.received.body.in_block_list
    block_list = db.session.query(BlockList).filter(BlockList.subject == g.user, BlockList.object_ == user)

    if in_block_list_mark and block_list is None:
        block_list = BlockList()
        block_list.subject = g.user
        block_list.object_ = user
        block_list.commit()
    if not in_block_list_mark and block_list is not None:
        block_list.delete()

    return make_response()
