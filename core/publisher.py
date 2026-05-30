import asyncio
import json
import time
import uuid
import traceback

import msgpack
from pika.spec import BasicProperties

from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger, settings


class BotPublisher:
    DEFAULT_TIMEOUT = 0.2
    SOCIAL_MEDIA = {"social_media": settings.SOCIAL_MEDIA}

    def __init__(self):

        self.rabbitmq = RabbitMQConnection()
        self.channel = self.rabbitmq.channel

        result = self.channel.queue_declare(
            queue='', exclusive=True, durable=True
        )
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
        )

        self.cor_id = None
        self.response = None

    def on_response(self, ch, method, properties, body):
        if self.cor_id == properties.correlation_id:
            self.response = msgpack.unpackb(body)

            ch.basic_ack(delivery_tag=method.delivery_tag)

    def publish(self, exchange: str, routing_key: str, message: dict, timeout: float = None) -> dict:
        try:
            self.response = None
            self.cor_id = str(uuid.uuid4())
            timeout = timeout or self.DEFAULT_TIMEOUT

            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                properties=BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=self.cor_id,
                ),
                body=msgpack.packb(message),
            )

            start_time = time.time()

            while self.response is None:
                if time.time() - start_time > timeout:
                    return None

                self.rabbitmq.connection.process_data_events(time_limit=0.1)

            return self.response

        except Exception as exc:
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(
                f"Publisher got error while publish \nto this exchange:{exchange}\nand this routing key:{routing_key}")

    def user_create(self, body, callback, callback_kwargs):
        try:
            message = body | self.SOCIAL_MEDIA
            response = self.publish(exchange="user", routing_key="user.create", message=message)
            self.run_callback(callback, callback_kwargs, {"response": response})

        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)

    def user_phone_number_check(self, body, callback, callback_kwargs):
        try:
            response = self.publish(exchange="user", routing_key="user.check_phone_number", message=body)
            self.run_callback(callback, callback_kwargs, {"response": response})

        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)

    def user_join_from_different_platform(self, body, callback, callback_kwargs):
        try:
            message = body | self.SOCIAL_MEDIA
            response = self.publish(exchange="user", routing_key="user.join", message=message)
            self.run_callback(callback, callback_kwargs, {"response": response})
        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)

    def get_user_by_username(self, body, callback, callback_kwargs):
        message = body | self.SOCIAL_MEDIA
        response = self.publish(exchange="user", routing_key="user.get_user_by_username", message=message)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def check_admin_menu_permission(self, body, callback, callback_kwargs):
        response = self.publish(exchange="user", routing_key="user.check_admin_menu_permission", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def create_role(self, body, callback, callback_kwargs):
        response = self.publish(exchange="role", routing_key="role.create", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    @staticmethod
    def run_callback(callback, callback_kwargs, response):
        try:
            response["response"] = json.loads(response["response"])
            callback_kwargs |= response
            asyncio.create_task(callback(**callback_kwargs))
        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)
