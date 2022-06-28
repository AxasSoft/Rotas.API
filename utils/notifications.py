from abc import abstractmethod, ABC

from pyfcm import FCMNotification

from app.models import Notification, Device


class BaseConsumer(ABC):

    @abstractmethod
    def notify(self, recipient, text: str):
        pass


class TerminalConsumer(BaseConsumer):
    def notify(self, recipient, text: str):
        print(f'''New notification:
        
recipient: {recipient}
text: {text}

''')


class DbConsumer(BaseConsumer):

    def notify(self, recipient, text: str):
        notification = Notification()
        notification.user = recipient
        notification.text = text
        notification.commit()


class FbConsumer(BaseConsumer):

    def __init__(self, api_key: str):
        self.push_service = FCMNotification(api_key=api_key)

    def notify(self, recipient, text: str):
        registration_ids = [
            device.firebase_id
            for device
            in Device.query.filter(
                Device.user == recipient,
                Device.firebase_id != None,
                Device.enable_notification
            ).all()
        ]

        print(registration_ids)

        if len(registration_ids) > 0:
            result = self.push_service.notify_multiple_devices(
                registration_ids=list(set(
                    device.firebase_id
                    for device
                    in Device.query.filter(
                        Device.user_id == recipient.pk,
                        Device.firebase_id != None,
                        Device.enable_notification
                    ).all()
                )),
                message_title='Новое уведомление',
                message_body=text
            )
            print(result)
        else:
            print('No devices')


class Notificator:

    def __init__(self):
        self.consumers = []

    def notify(self, recipient, text: str):
        for consumer in self.consumers:
            try:
                consumer.notify(recipient=recipient, text=text)
            except Exception as ex:
                print(ex)

