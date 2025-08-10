import json
from multiprocessing.connection import Connection
import os

from datetime import datetime
import traceback
import asyncio
from utils.log import log
from utils.handleMessage import sendMessage
import time

import redis



from .Worker  import Worker
class CacheWorker(Worker):
    #################
    # dont edit this part
    ################
    isBusy: bool = False
    redisInstance: redis.Redis
    prefixKey: str = "CACHE_CHATBOT_"
    conn: Connection
    
    def __init__(self, conn: Connection, config: dict):
        CacheWorker.conn = conn
        self.redis_connection_string = config.get("redis_url", "redis://localhost:6379/0")
        self.redis_port = config.get("redis_port", 6379)
        self.redisUsername = config.get("redis_username", "")
        self.redisPassword = config.get("redis_password", "")
        self.redisPort = config.get("redis_password", 6379)
    
    def run(self) -> None:
        try:
            # Initialize Redis connection with proper authentication
            if self.redisUsername and self.redisPassword:
                self.redisInstance = redis.Redis.from_url(
                    self.redis_connection_string,
                    username=self.redisUsername,
                    password=self.redisPassword,
                    port=self.redis_port,
                    decode_responses=True
                )
            else:
                self.redisInstance = redis.Redis.from_url(
                    self.redis_connection_string,
                    port=self.redis_port,
                    decode_responses=True
                )
            
            # Test Redis connection
            self.redisInstance.ping()
            log("Redis connection established successfully", 'info')
            
        except Exception as e:
            log(f"Failed to connect to Redis: {e}", 'error')
            return
        
        # Start the async tasks
        asyncio.run(self.listen_task())

    async def listen_task(self):
        print("CacheWorker is listening for messages...")
        while True:
            try:
                # Change poll(1) to poll(0.1) to reduce blocking time
                if CacheWorker.conn.poll(0.1):  # Shorter timeout
                    message = self.conn.recv()
                    if self.isBusy:
                        print("CacheWorker is busy, ignoring message.")
                        self.sendToOtherWorker(
                            messageId=message.get("messageId"),
                            destination=message.get("destination", []),
                            data=message.get("data", {}),
                            status="failed",
                            reason="SERVER_BUSY"
                        )
                        continue
                    
                    self.isBusy = True
                    
                    try:
                        dest = [
                            d
                            for d in message["destination"]
                            if d.split("/", 1)[0] == "CacheWorker"
                        ]
                        
                        if not dest:
                            log("No valid destination found for CacheWorker", 'warning')
                            continue
                            
                        destSplited = dest[0].split('/')
                        if len(destSplited) < 2:
                            log("Invalid destination format", 'error')
                            continue
                            
                        method = destSplited[1]
                        param = destSplited[2] if len(destSplited) > 2 else None
                        
                        instance_method = getattr(self, method, None)
                        if not instance_method:
                            log(f"Method {method} not found", 'error')
                            continue
                            
                        # Call the method with appropriate parameters
                        if param:
                            result = instance_method(id=param, data=message.get("data", {}))
                        else:
                            result = instance_method(data=message.get("data", {}))
                            
                        sendMessage(
                            conn=self.conn, 
                            status="completed",
                            destination=result["destination"],
                            messageId=message["messageId"],
                            data=result.get('data', []),
                        )
                        
                    except Exception as e:
                        log(f"Error processing message: {e}", 'error')
                        traceback.print_exc()
                        sendMessage(
                            conn=self.conn, 
                            status="failed",
                            destination=message.get("destination", []),
                            messageId=message.get("messageId"),
                            data={"error": str(e)},
                        )
                    finally:
                        self.isBusy = False
          
            except EOFError:
                log("Connection closed by supervisor", 'error')
                break
            except Exception as e:
                traceback.print_exc()
                print(e)
                log(f"Message loop error: {e}", 'error')
                break
            await asyncio.sleep(0.1)  # Sleep to prevent busy-waiting

    def sendToOtherWorker(self, messageId: str, destination: list, data: dict, status: str, reason: str = ""):
        """Helper method to send messages to other workers"""
        try:
            sendMessage(
                conn=self.conn,
                messageId=messageId,
                destination=destination,
                data={"reason": reason, **data},
                status=status
            )
        except Exception as e:
            log(f"Error sending message to other worker: {e}", 'error')

    #########################################
    # Cache Methods
    #########################################
    
    def set(self, id: str = None, data: dict = None) -> dict:
        """
        Set a key-value pair in the cache
        Expected data format: {"key": "cache_key", "value": "cache_value", "ttl": 3600}
        """
        try:
            if not data:
                return {
                    "destination": ["error"],
                    "data": {"error": "No data provided"}
                }
            
            key = data.get("key")
            value = data.get("value")
            ttl = data.get("ttl", 3600)  # Default TTL: 1 hour
            
            if not key:
                return {
                    "destination": ["supervisor"],
                    "data": {"error": "Key is required"}
                }
            
            # Add prefix to key
            full_key = f"{self.prefixKey}{key}"
            
            # Convert value to JSON string if it's not already a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            # Set the value with TTL
            if ttl > 0:
                self.redisInstance.setex(full_key, ttl, value)
            else:
                self.redisInstance.set(full_key, value)
            
            log(f"Cache set: {full_key}", 'info')
            
            return {
                "destination": ["supervisor"],
                "data": {
                    "message": "Cache set successfully",
                    "key": key,
                    "full_key": full_key,
                    "ttl": ttl
                }
            }
            
        except Exception as e:
            log(f"Error setting cache: {e}", 'error')
            return {
                "destination": ["error"],
                "data": {"error": f"Failed to set cache: {str(e)}"}
            }
    
    def getByKey(self, id: str = None, data: dict = None) -> dict:
        """
        Get a value from cache by key
        Uses 'id' parameter as the key, or data["key"] if id is not provided
        """
        try:
            # Use id parameter as key, or fallback to data["key"]
            key = id or (data.get("key") if data else None)

            # Add prefix to key
            full_key = f"{self.prefixKey}{key}"
            
            # Get the value
            value = self.redisInstance.get(full_key)
            
            if value is None:
                return {
                    "destination": ["GraphQLWorker/onProcessed/"],
                    "data":[]
                }
            
            # Try to parse JSON, if it fails return as string
            try:
                parsed_value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = value
            
            # Get TTL for additional info
            ttl = self.redisInstance.ttl(full_key)
            
            log(f"Cache retrieved: {full_key}", 'info')
            
            return {
                "destination": ["GraphQLWorker/onProcessed/"],
                "data": parsed_value if parsed_value is not None else value,
            }
            
        except Exception as e:
            log(f"Error getting cache: {e}", 'error')
            return {
                "destination": ["error"],
                "data": {"error": f"Failed to get cache: {str(e)}"}
            }
    
    def getAll(self, id: str = None, data: dict = None) -> dict:
        """
        Get all cached data with the prefix
        Optional data parameters: {"pattern": "*", "limit": 100}
        """
        try:
            pattern = data.get("pattern", "*") if data else "*"
            limit = data.get("limit", 100) if data else 100
            
            # Search for keys with prefix
            search_pattern = f"{self.prefixKey}{pattern}"
            keys = []
            
            # Use scan_iter for better performance with large datasets
            for key in self.redisInstance.scan_iter(match=search_pattern, count=limit):
                keys.append(key)
                if len(keys) >= limit:
                    break
            
            if not keys:
                return {
                    "destination": ["success"],
                    "data": {
                        "message": "No cached data found",
                        "pattern": search_pattern,
                        "count": 0,
                        "items": []
                    }
                }
            
            # Get all values for the keys
            items = []
            for key in keys:
                try:
                    value = self.redisInstance.get(key)
                    if value is not None:
                        # Try to parse JSON
                        try:
                            parsed_value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            parsed_value = value
                        
                        # Remove prefix for display
                        display_key = key.replace(self.prefixKey, "", 1)
                        ttl = self.redisInstance.ttl(key)
                        
                        items.append({
                            "key": display_key,
                            "full_key": key,
                            "value": parsed_value,
                            "ttl": ttl if ttl > 0 else "No expiration"
                        })
                except Exception as e:
                    log(f"Error processing key {key}: {e}", 'warning')
                    continue
            
            log(f"Cache getAll: Found {len(items)} items", 'info')
            
            return {
                "destination": ["success"],
                "data": {
                    "message": "Cache data retrieved successfully",
                    "pattern": search_pattern,
                    "count": len(items),
                    "items": items
                }
            }
            
        except Exception as e:
            log(f"Error getting all cache: {e}", 'error')
            return {
                "destination": ["error"],
                "data": {"error": f"Failed to get all cache: {str(e)}"}
            }

  
############### Helper function to convert ObjectId to string in a list of documents
  
  

def main(conn: Connection, config: dict):
    """Main entry point for the worker process"""
    worker = CacheWorker(conn, config)
    worker.run()