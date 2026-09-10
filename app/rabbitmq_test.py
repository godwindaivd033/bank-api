import pika
connection= pika.BlockingConnection(pika.ConnectionParameters(host= "localhost", port= 5672))

channel= connection.channel()
channel.queue_declare(queue= "email_queue", durable= "False")
channel.basic_publish(exchange= "", routing_key= "email_queue", body= "Hello, this is my first RabbitMQ message!")
print("connected to RabbitMQ!")
print("Meassage sent!")
connection.close()