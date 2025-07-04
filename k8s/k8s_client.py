from kubernetes import client, config

# init
config.load_kube_config()  # ~/.kube/config 자동으로 로드
v1_core = client.CoreV1Api()
v1_batch = client.BatchV1Api()
