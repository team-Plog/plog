from influxdb import InfluxDBClient
import os
from dotenv import load_dotenv

load_dotenv()
# client 초기화
client = InfluxDBClient(
    os.getenv("INFLUXDB_HOST"),
    os.getenv("INFLUXDB_PORT"),
    None,
    None,
    os.getenv("INFLUXDB_DATABASE"),
)
