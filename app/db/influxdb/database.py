from influxdb import InfluxDBClient

# client 초기화
client = InfluxDBClient(
    '35.216.24.11',
    31000,
    None,
    None,
    'k6'
)
