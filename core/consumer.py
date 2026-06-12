import asyncio
import threading
import traceback

import msgpack
from pika.adapters.blocking_connection import BlockingChannel
from pika import BasicProperties

from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger


class BotConsumer:
    EXCHANGE = "notify"

    def __init__(self, app):
        self.app = app
        self.loop: asyncio.AbstractEventLoop | None = None

    def start_consuming(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        try:
            rabbitmq = RabbitMQConnection()
            channel = rabbitmq.channel

            channel.exchange_declare(exchange=self.EXCHANGE, exchange_type="topic", durable=True)
            result = channel.queue_declare(queue="", exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange=self.EXCHANGE, queue=queue_name, routing_key="notify.*")
            channel.basic_consume(queue=queue_name, on_message_callback=self.on_notify, auto_ack=True)

            logger.info("BotConsumer: waiting for messages on notify exchange")
            channel.start_consuming()
        except Exception:
            logger.error(traceback.format_exc())

    def on_notify(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)

            if method.routing_key == "notify.loan_request":
                asyncio.run_coroutine_threadsafe(
                    self.app.handle_notify_loan_request(data),
                    self.loop,
                )

        except Exception:
            logger.error(traceback.format_exc())
