from kubernetes import client, config

# init
try:
    config.load_incluster_config()
    print("✅ In-cluster config loaded.")
except:
    config.load_kube_config()
    print("✅ Local config loaded.")

v1_core = client.CoreV1Api()
v1_batch = client.BatchV1Api()
v1_apps = client.AppsV1Api()
