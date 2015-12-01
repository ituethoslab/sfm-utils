import logging
from kombu import Connection, Queue, Exchange, Producer
from kombu.mixins import ConsumerMixin

log = logging.getLogger(__name__)

EXCHANGE = "sfm_exchange"


# Copied from https://github.com/celery/kombu/blob/master/kombu/mixins.py until in a kombu release.
class ConsumerProducerMixin(ConsumerMixin):
    """Version of ConsumerMixin having separate connection for also
    publishing messages.
    Example:
    .. code-block:: python
        class Worker(ConsumerProducerMixin):
            def __init__(self, connection):
                self.connection = connection
            def get_consumers(self, Consumer, channel):
                return [Consumer(queues=Queue('foo'),
                                 on_message=self.handle_message,
                                 accept='application/json',
                                 prefetch_count=10)]
            def handle_message(self, message):
                self.producer.publish(
                    {'message': 'hello to you'},
                    exchange='',
                    routing_key=message.properties['reply_to'],
                    correlation_id=message.properties['correlation_id'],
                    retry=True,
                )
    """
    _producer_connection = None

    def on_consume_end(self, connection, channel):
        if self._producer_connection is not None:
            self._producer_connection.close()
            self._producer_connection = None

    @property
    def producer(self):
        return Producer(self.producer_connection)

    @property
    def producer_connection(self):
        if self._producer_connection is None:
            conn = self.connection.clone()
            conn.ensure_connection(self.on_connection_error,
                                   self.connect_max_retries)
            self._producer_connection = conn
        return self._producer_connection


class BaseConsumer(ConsumerProducerMixin):
    """
    Base class for consuming messages from Rabbit.

    A BaseConsumer can be configured with an exchange and a mapping of
    queues to routing keys. Exchanges, queues, and bindings will
    be automatically created.

    Subclasses should override on_message().

    To send a message, use self.producer.publish().
    """
    def __init__(self, mq_config=None):
        self.mq_config = mq_config
        if self.mq_config and self.mq_config.host and self.mq_config.username and self.mq_config.password:
            self.connection = Connection(transport="librabbitmq",
                                         hostname=mq_config.host,
                                         userid=mq_config.username,
                                         password=mq_config.password)
            self.exchange = Exchange(name=self.mq_config.exchange,
                                     type="topic",
                                     durable=True)
        else:
            self.connection = None
            self.exchange = None

        self.message = None
        self.routing_key = None

    def get_consumers(self, Consumer, channel):
        assert self.mq_config

        # Declaring ourselves rather than use auto-declare.
        log.debug("Declaring %s exchange", self.mq_config.exchange)
        self.exchange(channel).declare()

        queues = []
        for queue_name, routing_keys in self.mq_config.queues.items():
            queue = Queue(name=queue_name,
                          exchange=self.exchange,
                          channel=channel,
                          durable=True)
            log.debug("Declaring queue %s", queue_name)
            queue.declare()
            for routing_key in routing_keys:
                log.debug("Binding queue %s to %s", queue_name, routing_key)
                queue.bind_to(exchange=self.exchange,
                              routing_key=routing_key)
            queues.append(queue)

        consumer = Consumer(queues=queues,
                            callbacks=[self._callback],
                            auto_declare=False)
        consumer.qos(prefetch_count=1, apply_global=True)
        return [consumer]

    def _callback(self, message, message_obj):
        """
        Callback for receiving harvest message.
        """
        self.routing_key = message_obj.delivery_info["routing_key"]
        self.message = message

        # Acknowledge the message
        message_obj.ack()

        self.on_message()

    def on_message(self):
        """
        Override this class to consume message.

        When called, self.routing_key and self.message
        will be populated based on the new message.
        """
        pass


class MqConfig:
    """
    Configuration for connecting to RabbitMQ.
    """
    def __init__(self, host, username, password, exchange, queues):
        """
        :param host: the host
        :param username: the username
        :param password: the password
        :param exchange: the exchange
        :param queues: map of queue names to lists of routing keys
        """
        self.host = host
        self.username = username
        self.password = password
        self.exchange = exchange
        self.queues = queues
