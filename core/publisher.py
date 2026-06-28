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

    def check_admin_menu_permission(self, body):
        response = self.publish(exchange="user", routing_key="user.check_admin_menu_permission", message=body)
        return json.loads(response)

    def check_loan_create_permission(self, body):
        response = self.publish(exchange="user", routing_key="user.check_loan_create_permission", message=body)
        return json.loads(response)

    def update_chat_id(self, body):
        try:
            message = body | self.SOCIAL_MEDIA
            self.publish(exchange="user", routing_key="user.update_chat_id", message=message)
        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)

    def create_loan_request(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.create", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def approve_loan(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.approve", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def reject_loan(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.reject", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_client_history(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.get_client_history", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_loans(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.get_loans", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def list_receipts(self, body, callback, callback_kwargs):
        response = self.publish(exchange="receipt", routing_key="receipt.list", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_receipt_proof(self, body):
        # Returns {"proof_type": "photo", "proof_bytes": <bytes>, "ext": ...} or
        # {"proof_type": "text", "proof_text": ...} or {"error": ...} / None.
        return self.publish(exchange="receipt", routing_key="receipt.get_proof", message=body, timeout=5.0)

    def approve_receipt(self, body, callback, callback_kwargs):
        response = self.publish(exchange="receipt", routing_key="receipt.approve", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def reject_receipt(self, body, callback, callback_kwargs):
        response = self.publish(exchange="receipt", routing_key="receipt.reject", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_bank_info(self, body, callback, callback_kwargs):
        response = self.publish(exchange="bank_info", routing_key="bank_info.get", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def save_bank_info(self, body, callback, callback_kwargs):
        response = self.publish(exchange="bank_info", routing_key="bank_info.save", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def create_receipt(self, body, callback, callback_kwargs):
        # Larger timeout: photo proofs carry image bytes and the backend writes a media file.
        response = self.publish(exchange="receipt", routing_key="receipt.create", message=body, timeout=5.0)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_pending_installments(self, body, callback, callback_kwargs):
        response = self.publish(exchange="installment_payment", routing_key="installment_payment.get_pending", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_balance(self, body, callback, callback_kwargs):
        response = self.publish(exchange="account", routing_key="account.get_balance", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_my_loans(self, body, callback, callback_kwargs):
        response = self.publish(exchange="loan", routing_key="loan.get_my_loans", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def list_my_receipts(self, body, callback, callback_kwargs):
        response = self.publish(exchange="receipt", routing_key="receipt.list_mine", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def list_my_transactions(self, body, callback, callback_kwargs):
        response = self.publish(exchange="transaction", routing_key="transaction.list_mine", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def create_role(self, body, callback, callback_kwargs):
        response = self.publish(exchange="role", routing_key="role.create", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_roles(self, body):
        response = self.publish(exchange="role", routing_key="role.get_all", message=body)
        return response

    def get_role_permissions(self, body):
        response = self.publish(exchange="permission", routing_key="permission.get_role_permission", message=body)

        return response

    def get_all_permissions(self, body):
        response = self.publish(exchange="permission", routing_key="permission.get_all", message=body)
        return response

    def add_role_permission(self, body):
        response = self.publish(exchange="permission", routing_key="permission.create", message=body)
        return response

    def revoke_role_permission(self, body):
        response = self.publish(exchange="permission", routing_key="permission.revoke", message=body)
        return response

    def delete_role(self, body):
        response = self.publish(exchange="role", routing_key="role.delete", message=body)
        return response

    def assign_user_role(self, body, callback, callback_kwargs):
        response = self.publish(exchange="role", routing_key="role.assign", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def get_user_roles(self, body, callback, callback_kwargs):
        response = self.publish(exchange="role", routing_key="role.get_user_roles", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    def revoke_user_role(self, body, callback, callback_kwargs):
        response = self.publish(exchange="role", routing_key="role.revoke", message=body)
        self.run_callback(callback, callback_kwargs, {"response": response})

    @staticmethod
    def run_callback(callback, callback_kwargs, response):
        try:
            logger.info(response)
            raw = response.get("response")
            if isinstance(raw, (str, bytes, bytearray)):
                response["response"] = json.loads(raw)
            callback_kwargs |= response
            asyncio.create_task(callback(**callback_kwargs))
        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)
