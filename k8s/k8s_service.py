import os

from dotenv import load_dotenv
from kubernetes import client
from k8s.k8s_client import v1_batch

load_dotenv()

# job 구조 job_spec -> template -> pod_spec
def create_k6_job_with_dashboard(job_name: str, script_filename: str, pvc_name: str="k6-script-pvc"):
    """
    지정된 PVC에 있는 k6 스크립트를 K6_WEB_DASHBOARD 옵션으로 실행하는 Job 생성
    """
    mount_path = os.getenv("K6_SCRIPT_FILE_FOLDER", '/mnt/k6-scripts')
    # mount_path = os.getenv("K6_SCRIPT_FILE_FOLDER")

    # 1. container 설정
    container = client.V1Container(
        name="k6",
        image="grafana/k6",
        command=["sh", "-c", f"K6_WEB_DASHBOARD=true k6 run {mount_path}/{script_filename}"],
        ports=[client.V1ContainerPort(container_port=5665)],
        volume_mounts=[
            client.V1VolumeMount(
                name="k6-script-volume",
                mount_path=f"{mount_path}"
            )
        ],
        env=[
            client.V1EnvVar(
                name="K6_OUT",
                value=f"influxdb=http://{os.getenv('INFLUXDB_HOST')}:{os.getenv('INFLUXDB_PORT')}/{os.getenv('INFLUXDB_DATABASE')}"
            )
        ],
        # TODO 리소스 요청량에 비례하여 할당
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
        metadata=client.V1ObjectMeta(labels=labels),
        spec=pod_spec
    )

    # job spec
    job_spec = client.V1JobSpec(
        template=template,
        ttl_seconds_after_finished=300  # 5분으로 연장하여 메트릭 수집 시간 확보
    )

    job = client.V1Job(
        metadata=client.V1ObjectMeta(name=job_name),
        spec=job_spec
    )

    v1_batch.create_namespaced_job(namespace="default", body=job)
    print(f"✅ Job '{job_name}' created to run '/{mount_path}/{script_filename}' with dashboard enabled.")
