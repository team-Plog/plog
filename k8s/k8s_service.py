from kubernetes import client
from k8s.k8s_client import v1_batch

# job 구조 job_spec -> template -> pod_spec
def create_k6_job_with_dashboard(job_name: str, script_filename: str, pvc_name: str="k6-script-pvc"):
    """
    지정된 PVC에 있는 k6 스크립트를 K6_WEB_DASHBOARD 옵션으로 실행하는 Job 생성
    """

    # 1. container 설정
    container = client.V1Container(
        name="k6",
        image="grafana/k6",
        command=["sh", "-c", f"K6_WEB_DASHBOARD=true k6 run /scripts/{script_filename}"],
        ports=[client.V1ContainerPort(container_port=5665)],
        volume_mounts=[
            client.V1VolumeMount(
                name="k6-script-volume",
                mount_path="/scripts"
            )
        ],
        env=[
            client.V1EnvVar(
                name="K6_OUT",
                value="influxdb=http://influxdb:8086/k6"
            )
        ],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "512Mi"},
            limits={"cpu": "1", "memory": "1Gi"}
        )
    )

    # 2. volume 설정
    volume = client.V1Volume(
        name="k6-script-volume",
        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
            claim_name=pvc_name
        )
    )

    labels = {"app": "k6-runner"}

    # job 내부 pod spec
    pod_spec = client.V1PodSpec(
        containers=[container],
        restart_policy="Never",
        volumes=[volume]
    )

    # job template
    template = client.V1PodTemplateSpec(
        spec=pod_spec
    )

    # job spec
    job_spec = client.V1JobSpec(
        template=template
    )

    job = client.V1Job(
        metadata=client.V1ObjectMeta(name=job_name, labels=labels),
        spec=job_spec
    )

    v1_batch.create_namespaced_job(namespace="default", body=job)
    print(f"✅ Job '{job_name}' created to run '/scripts/{script_filename}' with dashboard enabled.")
