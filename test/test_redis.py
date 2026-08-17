import redis




client= redis.Redis(host= "localhost",
                    port= 6379,
                    decode_responses= True)

client.set("message", "Hello Redis")

value= client.get("message")
print(value)