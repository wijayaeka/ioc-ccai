from huggingface_hub import HfApi

api = HfApi()
api.upload_folder(
    folder_path="results/model3/model_new",
    repo_id="captainrobotfly/ioc_v2",
    repo_type="model"
)
