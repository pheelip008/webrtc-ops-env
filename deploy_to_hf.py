"""
Deploy the WebRTC Ops Environment to Hugging Face Spaces.

Usage:
    python deploy_to_hf.py

Prerequisites:
    1. pip install huggingface_hub
    2. huggingface-cli login  (enter your HF token)
"""

import os
import shutil
import tempfile
from pathlib import Path
from huggingface_hub import HfApi, create_repo

# Configuration
REPO_ID = "pheelip0030/webrtc-ops-env"
ENV_DIR = Path(r"d:\pheelip\Scaler\webrtc_ops_env")

def main():
    api = HfApi()

    # 1. Create the Space (Docker SDK, with openenv tag)
    print(f"Creating HF Space: {REPO_ID}...")
    try:
        create_repo(
            repo_id=REPO_ID,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
        )
        print(f"  ✓ Space created/exists: https://huggingface.co/spaces/{REPO_ID}")
    except Exception as e:
        print(f"  Note: {e}")

    # 2. Upload all files
    print("\nUploading files...")

    # The README.md for HF must have the YAML frontmatter
    # We'll use README_HF.md as the HF README and keep our docs in a separate file
    hf_readme = ENV_DIR / "README_HF.md"
    readme = ENV_DIR / "README.md"

    # Combine HF frontmatter with our README content
    combined_readme = hf_readme.read_text() + "\n" + readme.read_text()
    combined_path = ENV_DIR / "_combined_readme.md"
    combined_path.write_text(combined_readme)

    # Upload the combined README as README.md on HF
    api.upload_file(
        path_or_fileobj=str(combined_path),
        path_in_repo="README.md",
        repo_id=REPO_ID,
        repo_type="space",
    )
    print("  ✓ README.md (with HF frontmatter)")

    # Upload Dockerfile at root
    api.upload_file(
        path_or_fileobj=str(ENV_DIR / "Dockerfile"),
        path_in_repo="Dockerfile",
        repo_id=REPO_ID,
        repo_type="space",
    )
    print("  ✓ Dockerfile")

    # Upload all Python/YAML/TOML files
    files_to_upload = [
        ("inference.py", "inference.py"),
        ("__init__.py", "__init__.py"),
        ("models.py", "models.py"),
        ("client.py", "client.py"),
        ("openenv.yaml", "openenv.yaml"),
        ("pyproject.toml", "pyproject.toml"),
        (".dockerignore", ".dockerignore"),
        ("server/__init__.py", "server/__init__.py"),
        ("server/app.py", "server/app.py"),
        ("server/webrtc_environment.py", "server/webrtc_environment.py"),
        ("server/requirements.txt", "server/requirements.txt"),
    ]

    for local_path, repo_path in files_to_upload:
        full_path = ENV_DIR / local_path
        if full_path.exists():
            api.upload_file(
                path_or_fileobj=str(full_path),
                path_in_repo=repo_path,
                repo_id=REPO_ID,
                repo_type="space",
            )
            print(f"  ✓ {repo_path}")
        else:
            print(f"  ✗ MISSING: {local_path}")

    # Clean up temp file
    combined_path.unlink(missing_ok=True)

    print(f"\n{'='*50}")
    print(f"✅ Deployment complete!")
    print(f"   Space URL: https://huggingface.co/spaces/{REPO_ID}")
    print(f"   App URL:   https://{REPO_ID.replace('/', '-')}.hf.space")
    print(f"{'='*50}")
    print(f"\nThe Space will now build the Docker image automatically.")
    print(f"Check build status at: https://huggingface.co/spaces/{REPO_ID}/logs")


if __name__ == "__main__":
    main()
