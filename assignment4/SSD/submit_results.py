import pathlib
import tqdm
import torch
import json
from PIL import Image
from ssd.config.defaults import cfg
from ssd.config.path_catlog import DatasetCatalog
from ssd.data.datasets import TDT4265Dataset
import argparse
import numpy as np
from ssd import torch_utils
from ssd.data.transforms import build_transforms
from ssd.modeling.detector import SSDDetector
from ssd.utils.checkpoint import CheckPointer


def read_labels(json_path):
    assert json_path.is_file(), f"Did not find labels at: {json_path}"
    with open(json_path, "r") as fp:
        labels = json.load(fp)
    return labels


def check_all_images_exists(labels,  image_paths):
    image_ids = set([int(x.stem) for x in image_paths])
    for image in labels["images"]:
        image_id = image["id"]
        assert image_id in image_ids,\
            f"Image ID missing: {image_id}"
    return


@torch.no_grad()
def get_detections(cfg, ckpt):
    model = SSDDetector(cfg)
    model = torch_utils.to_cuda(model)
    checkpointer = CheckPointer(model, save_dir=cfg.OUTPUT_DIR)
    checkpointer.load(ckpt, use_latest=ckpt is None)
    weight_file = ckpt if ckpt else checkpointer.get_checkpoint_file()
    print('Loaded weights from {}'.format(weight_file))

    dataset_path = DatasetCatalog.DATASETS["coco_traffic_test"]["data_dir"]
    dataset_path = pathlib.Path(cfg.DATASET_DIR, dataset_path)
    image_dir = dataset_path
    image_paths = list(image_dir.glob("*.jpg"))

    transforms = build_transforms(cfg, is_train=False)
    model.eval()
    detections = []
    labels = read_labels(image_dir.parent.parent.joinpath("test_labels_mini.json"))
    check_all_images_exists(labels, image_paths)
    # Filter labels on if they are test and only take the 7th frame
    images = labels["images"]
    for i, label in enumerate(tqdm.tqdm(images)):
        image_id = label["id"]
        image_path = image_dir.joinpath(label["file_name"])
        image = np.array(Image.open(image_path).convert("RGB"))
        height, width = image.shape[:2]
        images = transforms(image)[0].unsqueeze(0)
        result = model(torch_utils.to_cuda(images))[0]
        result = result.resize((width, height)).cpu().numpy()
        boxes, labels, scores = result['boxes'], result['labels'], result['scores']
        for idx in range(len(boxes)):
            box = boxes[idx]
            label_id = labels[idx]
            score = float(scores[idx])
            assert box.shape == (4,)
            json_box = {
                "image_id" : int(image_id),
                "category_id" : int(label_id),
                "bbox" : [int(box[0]), int(box[1]), int(box[2] - box[0]), int(box[3] - box[1])],
                "score" : float(score)  
            }
            detections.append(json_box)
    return detections


def dump_detections(cfg, detections, path):
    path.parent.mkdir(exist_ok=True, parents=True)
    with open(path, "w") as fp:
        json.dump(detections, fp)
    print("Detections saved to:", path)
    print("Abolsute path:", path.absolute())
    print("Go to: https://tdt4265-annotering.idi.ntnu.no/submissions/ to submit your result")


def main():
    parser = argparse.ArgumentParser(description="SSD Demo.")
    parser.add_argument(
        "config_file",
        default="",
        metavar="FILE",
        help="path to config file",
        type=str,
    )
    parser.add_argument("--ckpt", type=str, default=None, help="Trained weights.")
    parser.add_argument(
        "--opts",
        help="Modify config opions using the command-line",
        default=None,
        nargs=argparse.REMAINDER,
    )
    args = parser.parse_args()

    cfg.merge_from_file(args.config_file)
    #cfg.merge_from_list(args.opts)
    cfg.freeze()
    detections = get_detections(
        cfg=cfg,
        ckpt=args.ckpt)
    json_path = pathlib.Path(cfg.OUTPUT_DIR, "test_detected_boxes.json")
    dump_detections(cfg, detections, json_path)


if __name__ == '__main__':
    main()
