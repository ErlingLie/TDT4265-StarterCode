import json


def train_val_split(master_source, train_split_path, val_split_path, train_val_ratio = 0.8):
    with open(master_source, "r") as json_file:
        master = json.load(json_file)

    train = {k: v for k,v in master.items()}
    train["annotations"] = master["annotations"][0:int(train_val_ratio*len(master["annotations"]))]
    highest_image_id = train["annotations"][-1]["image_id"]
    images = []
    for image in master["images"]:
        if image["id"] <= highest_image_id:
            images.append(image)
    train["images"] = images
    with open(train_split_path, "w") as json_file:
        json.dump(train, json_file)


    test = {k : v for k,v in master.items()}
    test["annotations"] = master["annotations"][int(train_val_ratio*len(master["annotations"])):]
    lowest_image_id = test["annotations"][0]["image_id"]
    images = []
    for image in master["images"]:
        if image["id"] >= lowest_image_id:
            images.append(image)
    test["images"] = images
    with open(val_split_path, "w") as json_file:
        json.dump(test, json_file)

