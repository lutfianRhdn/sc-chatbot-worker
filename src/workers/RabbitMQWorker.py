import asyncio
import json
from multiprocessing.connection import Connection
import threading
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
import traceback
import pika 

from .Worker import Worker

class RabbitMQWorker(Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    
    string_connection:str
    connection: pika.BlockingConnection
    
    consumeQueue:str
    consumeChannel:pika.adapters.blocking_connection.BlockingChannel
    consumeCompensationQueue:str
    
    produceQueue:str
    produceChannel:pika.adapters.blocking_connection.BlockingChannel
    produceCompensationQueue:str
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, config:dict):
        # assign here
        RabbitMQWorker.conn = conn

        #### add your worker initialization code here
        try:
          self.consumeQueue = config.get("consumeQueue", "consume_queue")
          self.consumeCompensationQueue = config.get("consumeCompensationQueue", "consume_compensation_queue")
          self.produceQueue = config.get("produceQueue", "produce_queue")
          self.produceCompensationQueue = config.get("produceCompensationQueue", "produce_compensation_queue")
          
          # Initialize RabbitMQ connection
          parameters = pika.URLParameters(config['connection_string'])
          self.parameters = parameters
          self.connection = pika.BlockingConnection(parameters)
          self.consumeChannel = self.connection.channel()
          self.produceChannel = self.connection.channel()
          
          # Declare queues
          
          self.consumeChannel.queue_declare(queue=self.consumeQueue, durable=True)
          self.consumeChannel.queue_bind(queue=self.consumeQueue, exchange='topicExchange', routing_key=self.consumeQueue)
          self.consumeChannel.queue_declare(queue=self.consumeCompensationQueue, durable=True)
          self.produceChannel.queue_declare(queue=self.produceQueue, durable=True)
          self.produceChannel.queue_declare(queue=self.produceCompensationQueue, durable=True)
          
          t1 = threading.Thread(target=self.consumeMessage)
          t1.daemon = True  # Daemonize thread
          t1.start()  # Start the thread
          
          asyncio.run(self.listen_task())  # Start the async listener task          
            
        except Exception as e:
          traceback.print_exc()

          print(e)
          
          log(f"Failed to connect to RabbitMQ: {e}", "error")
          return

    async def listen_task(self):
        while True:
            try:
                if RabbitMQWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "RabbitMQWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(param,message['data'])
                    await asyncio.sleep(0.1)  # Yield control to the event loop
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=RabbitMQWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
    def consumeMessage(self) :
        
      print(f"[*] Waiting for messages in queue: {self.consumeQueue}")
      def callback(ch, method, properties, body):
        print(f"[x] Received message: {body.decode()}")
        self.sendToOtherWorker(
            destination=[
                'VectorWorker/runCreating/',
                'PromptRecommendationWorker/generatePrompt/',
                ],
            messageId=str(uuid.uuid4()),
            data=convertMessage(body.decode())
        )
        # Optional: acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

      print(f"[*] Starting to consume from queue: {self.consumeQueue}")
      self.consumeChannel.basic_qos(prefetch_count=1)
      self.consumeChannel.basic_consume(queue=self.consumeQueue, on_message_callback=callback)

      try:
          self.consumeChannel.start_consuming()
      except KeyboardInterrupt:
          self.consumeChannel.stop_consuming()
          print("[*] Stopped consuming")
      except Exception as e:
          log(f"Error consuming from queue: {e}", 'error')
    def produceMessage(self, queue_name: str, data: dict) -> None:
        try:
            connection = pika.BlockingConnection(self.parameters)
            produceChannel = connection.channel()
            produceChannel.queue_declare(queue=queue_name, durable=True)
            produceChannel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(data),
                properties=pika.BasicProperties(
                     headers={
                        'project_id': data.get('project_id', ''),
                    },
                    delivery_mode=2,  # make message persistent
                )
            )
            produceChannel.close()
            connection.close()
             
            print(f"[x] Sent message to queue: {queue_name}")
        except Exception as e:
            log(f"Error producing message to queue {queue_name}: {e}", 'error')
def main(conn: Connection, config: dict):
    worker = RabbitMQWorker()
    worker.run(conn, config)
