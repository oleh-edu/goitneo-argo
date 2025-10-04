#!/usr/bin/env python3
import os
import sys
import mlflow
from mlflow.tracking import MlflowClient


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise SystemExit(f"Missing required env var: {name}")
    return val


def get_accuracy_for_run(client: MlflowClient, run_id: str) -> float:
    try:
        hist = client.get_metric_history(run_id, "accuracy")
        if not hist:
            return float("-inf")
        return max(m.value for m in hist)
    except Exception:
        return float("-inf")


def select_candidate_version(client: MlflowClient, model_name: str, run_id: str | None, source_stage: str) -> tuple[str | None, float]:
    candidate_version = None
    candidate_acc = float("-inf")

    if run_id:
        versions = client.search_model_versions(f"name = '{model_name}' and run_id = '{run_id}'")
        if not versions:
            raise SystemExit(f"No model version found for run_id={run_id}")
        versions = sorted(versions, key=lambda v: int(v.version), reverse=True)
        v = versions[0]
        return v.version, get_accuracy_for_run(client, v.run_id)

    # Fetch all versions and filter by stage client-side (for older MLFlow servers)
    versions = list(client.search_model_versions(f"name = '{model_name}'"))
    if source_stage != "Any":
        versions = [v for v in versions if (getattr(v, "current_stage", None) or "None") == source_stage]

    for v in versions:
        acc = get_accuracy_for_run(client, v.run_id)
        if acc > candidate_acc:
            candidate_acc = acc
            candidate_version = v.version

    return candidate_version, candidate_acc

def archive_current_in_stage(client: MlflowClient, model_name: str, target_stage: str, skip_version: str | None):
    if not target_stage:
        return
    # Fetch all and filter client-side instead of querying by current_stage
    versions = list(client.search_model_versions(f"name = '{model_name}'"))
    current = [v for v in versions if (getattr(v, "current_stage", None) or "") == target_stage]
    for v in current:
        if skip_version and v.version == skip_version:
            continue
        print(f"Archiving current {target_stage} version={v.version}")
        client.transition_model_version_stage(name=model_name, version=v.version, stage="Archived")


def promote_version(client: MlflowClient, model_name: str, version: str, target_stage: str):
    print(f"Promoting version={version} to stage={target_stage}")
    client.set_registered_model_alias(name=model_name, alias=target_stage.lower(), version=version)
    print("Promotion completed.")


def main():
    # configuration
    tracking_uri = get_env("MLFLOW_TRACKING_URI", required=True)
    model_name = get_env("REGISTERED_MODEL_NAME", required=True)
    target_stage = get_env("TARGET_STAGE", "Production")
    source_stage = get_env("SOURCE_STAGE", "Any")
    min_accuracy = float(get_env("PROMOTE_MIN_ACCURACY", "0.9"))
    run_id = os.getenv("PROMOTE_RUN_ID")
    dry_run = get_env("PROMOTE_DRY_RUN", "false").lower() == "true"
    archive_existing = get_env("PROMOTE_ARCHIVE_OLD", "true").lower() == "true"

    # setup
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    print(f"Using MLflow at {tracking_uri}")
    print(f"Model: {model_name} -> Stage: {target_stage}")
    print(f"Constraints: min_accuracy={min_accuracy}, source_stage={source_stage}, run_id={run_id or 'auto-select'}")
    print(f"Options: dry_run={dry_run}, archive_existing={archive_existing}")

    # select candidate
    candidate_version, candidate_acc = select_candidate_version(client, model_name, run_id, source_stage)
    if candidate_version is None:
        raise SystemExit("No candidate model version found to promote.")
    print(f"Selected candidate version={candidate_version} accuracy={candidate_acc:.6f}")

    # threshold check
    if candidate_acc < min_accuracy:
        raise SystemExit(f"Candidate accuracy {candidate_acc:.6f} < required {min_accuracy:.6f}. Abort.")

    # dry run
    if dry_run:
        print("[DRY RUN] Would transition:")
        print(f" - Model {model_name} version {candidate_version} -> stage {target_stage}")
        if archive_existing:
            print(f" - Would archive existing versions currently in {target_stage}")
        return

    # archive and promote
    if archive_existing:
        archive_current_in_stage(client, model_name, target_stage, skip_version=candidate_version)
    promote_version(client, model_name, candidate_version, target_stage)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        eprint(str(e))
        sys.exit(1)
    except Exception as e:
        eprint(f"Unexpected error: {e}")
        sys.exit(1)
