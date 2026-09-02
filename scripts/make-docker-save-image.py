#!/usr/bin/env python3
import argparse
import copy
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
from datetime import datetime, timezone


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def add_file_to_tar(tar, name, data, mode=0o644):
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


def make_app_layer(jar_path):
    with open(jar_path, "rb") as f:
        jar_data = f.read()

    layer_buf = io.BytesIO()
    with tarfile.open(fileobj=layer_buf, mode="w") as layer_tar:
        add_file_to_tar(layer_tar, "app.jar", jar_data)

    return layer_buf.getvalue()


def blob_path(root, digest):
    algo, value = digest.split(":", 1)
    return os.path.join(root, "blobs", algo, value)


def write_blob(root, data):
    digest = "sha256:" + sha256_bytes(data)
    path = blob_path(root, digest)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return digest, len(data)


def build_oci_layout(tmp, jar_path, tag, port):
    index_path = os.path.join(tmp, "index.json")
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    descriptors = index.get("manifests", [])
    if not descriptors:
        raise RuntimeError("OCI index has no manifests")

    descriptor = None
    for item in descriptors:
        platform = item.get("platform", {})
        if platform.get("os") == "linux" and platform.get("architecture") == "amd64":
            descriptor = item
            break
    if descriptor is None:
        descriptor = descriptors[0]

    with open(blob_path(tmp, descriptor["digest"]), "rb") as f:
        manifest = json.load(f)

    with open(blob_path(tmp, manifest["config"]["digest"]), "rb") as f:
        config = json.load(f)

    layer_data = make_app_layer(jar_path)
    layer_diff_digest = "sha256:" + sha256_bytes(layer_data)
    gzip_buf = io.BytesIO()
    with gzip.GzipFile(fileobj=gzip_buf, mode="wb", mtime=0) as gz:
        gz.write(layer_data)
    compressed_layer = gzip_buf.getvalue()
    layer_digest, layer_size = write_blob(tmp, compressed_layer)

    new_config = copy.deepcopy(config)
    new_config["created"] = datetime.now(timezone.utc).isoformat()
    new_config["architecture"] = "amd64"
    new_config["os"] = "linux"
    new_config.setdefault("config", {})
    new_config["config"]["Entrypoint"] = ["java", "-jar", "/app.jar"]
    new_config["config"]["Cmd"] = None
    new_config["config"].setdefault("ExposedPorts", {})
    new_config["config"]["ExposedPorts"][f"{port}/tcp"] = {}
    new_config.setdefault("rootfs", {})
    new_config["rootfs"].setdefault("type", "layers")
    new_config["rootfs"].setdefault("diff_ids", [])
    new_config["rootfs"]["diff_ids"].append(layer_diff_digest)
    new_config.setdefault("history", [])
    new_config["history"].append({
        "created": new_config["created"],
        "created_by": "COPY app.jar /app.jar",
        "comment": "generated without docker daemon",
    })

    config_data = json.dumps(new_config, separators=(",", ":"), sort_keys=True).encode("utf-8")
    config_digest, config_size = write_blob(tmp, config_data)

    new_manifest = copy.deepcopy(manifest)
    new_manifest["config"] = {
        "mediaType": manifest["config"].get("mediaType", "application/vnd.oci.image.config.v1+json"),
        "digest": config_digest,
        "size": config_size,
    }
    new_manifest.setdefault("layers", [])
    new_manifest["layers"].append({
        "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        "digest": layer_digest,
        "size": layer_size,
    })

    manifest_data = json.dumps(new_manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    manifest_digest, manifest_size = write_blob(tmp, manifest_data)

    index["manifests"] = [{
        "mediaType": descriptor.get("mediaType", "application/vnd.oci.image.manifest.v1+json"),
        "digest": manifest_digest,
        "size": manifest_size,
        "platform": {"architecture": "amd64", "os": "linux"},
        "annotations": {"org.opencontainers.image.ref.name": tag},
    }]
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"), sort_keys=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Docker save tar exported from the base image")
    parser.add_argument("--jar", required=True, help="Spring Boot executable jar")
    parser.add_argument("--tag", required=True, help="Target image tag")
    parser.add_argument("--port", required=True, help="Container port")
    parser.add_argument("--output", required=True, help="Output Docker save tar")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(args.base, "r") as base_tar:
            base_tar.extractall(tmp)

        if os.path.exists(os.path.join(tmp, "index.json")) and os.path.exists(os.path.join(tmp, "oci-layout")):
            build_oci_layout(tmp, args.jar, args.tag, args.port)
            with tarfile.open(args.output, "w") as out_tar:
                for name in sorted(os.listdir(tmp)):
                    out_tar.add(os.path.join(tmp, name), arcname=name)
            return

        manifest_path = os.path.join(tmp, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if not manifest:
            raise RuntimeError("base image manifest is empty")

        item = manifest[0]
        config_path = os.path.join(tmp, item["Config"])
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        layer_data = make_app_layer(args.jar)
        layer_digest = sha256_bytes(layer_data)
        layer_dir = os.path.join(tmp, layer_digest)
        os.makedirs(layer_dir, exist_ok=True)

        with open(os.path.join(layer_dir, "layer.tar"), "wb") as f:
            f.write(layer_data)
        with open(os.path.join(layer_dir, "VERSION"), "w", encoding="utf-8") as f:
            f.write("1.0\n")
        with open(os.path.join(layer_dir, "json"), "w", encoding="utf-8") as f:
            json.dump({"id": layer_digest}, f)

        new_config = copy.deepcopy(config)
        new_config["created"] = datetime.now(timezone.utc).isoformat()
        new_config["architecture"] = "amd64"
        new_config["os"] = "linux"
        new_config.setdefault("config", {})
        new_config["config"]["Entrypoint"] = ["java", "-jar", "/app.jar"]
        new_config["config"]["Cmd"] = None
        new_config["config"].setdefault("ExposedPorts", {})
        new_config["config"]["ExposedPorts"][f"{args.port}/tcp"] = {}
        new_config.setdefault("rootfs", {})
        new_config["rootfs"].setdefault("type", "layers")
        new_config["rootfs"].setdefault("diff_ids", [])
        new_config["rootfs"]["diff_ids"].append(f"sha256:{layer_digest}")
        new_config.setdefault("history", [])
        new_config["history"].append({
            "created": new_config["created"],
            "created_by": "COPY app.jar /app.jar",
            "comment": "generated without docker daemon",
        })

        config_data = json.dumps(new_config, separators=(",", ":"), sort_keys=True).encode("utf-8")
        config_digest = sha256_bytes(config_data)
        new_config_name = f"{config_digest}.json"
        with open(os.path.join(tmp, new_config_name), "wb") as f:
            f.write(config_data)

        item["Config"] = new_config_name
        item["RepoTags"] = [args.tag]
        item["Layers"].append(f"{layer_digest}/layer.tar")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        if os.path.exists(config_path):
            os.remove(config_path)

        with tarfile.open(args.output, "w") as out_tar:
            for name in sorted(os.listdir(tmp)):
                out_tar.add(os.path.join(tmp, name), arcname=name)


if __name__ == "__main__":
    main()
